"""Authoritative scheduling engine: conflict flagging + downstream cascade.

This is the server-side mirror of the frontend `useScheduleEngine` composable. The
algorithm is PURE (operates on plain task/edge dicts) so the two implementations
stay line-for-line in sync and are pinned by shared test vectors. The client runs
the same logic for instant Gantt feedback; the server is authoritative — it stores
the conflict flags (so Desk/reports/other users see them) and commits cascades.

Dependency model (ERPNext-native): edges live on Task.depends_on, whose `task`
field is the PREDECESSOR, enriched with custom fields dependency_type (FS/SS/FF)
and lag_days. Successors are inferred by reversing the edge set. Calendar days
only (no working-day calendar). Milestones are single-date nodes (exp_end_date is
the due date; exp_start_date stays empty).
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate

VALID_DEP_TYPES = ("FS", "SS", "FF")


# --- pure date helpers (mirror _scheduleAddDays / _scheduleDiffDays) -----------


def _add_days(d, days):
	if not d:
		return None
	return getdate(d) + timedelta(days=int(days or 0))


def _diff_days(frm, to):
	# Calendar-day delta (to - frm); positive when to > frm.
	if not frm or not to:
		return 0
	return (getdate(to) - getdate(frm)).days


def _iso(d):
	return d.isoformat() if d else None


# --- pure graph algorithm (mirror the prototype engine) -----------------------


def _earliest_start_for_edge(pred, succ, dep, succ_duration_override=None):
	"""Earliest allowed start date for `succ` given one predecessor edge `dep`.

	Milestone predecessor: every dep type collapses to "milestone date + lag"
	(no span). Milestone successor: duration = 0.
	"""
	if not pred or not succ or not dep:
		return None
	lag = int(dep.get("lag") or 0)
	dtype = dep.get("type")
	pred_is_ms = pred.get("type") == "Milestone"
	succ_is_ms = succ.get("type") == "Milestone"
	if succ_is_ms:
		succ_dur = 0
	elif succ_duration_override is not None:
		succ_dur = succ_duration_override
	else:
		succ_dur = _diff_days(succ.get("start"), succ.get("end"))

	if dtype == "FS":
		if not pred.get("end"):
			return None
		return _add_days(pred.get("end"), lag)
	if dtype == "SS":
		anchor = pred.get("end") if pred_is_ms else pred.get("start")
		if not anchor:
			return None
		return _add_days(anchor, lag)
	if dtype == "FF":
		if not pred.get("end"):
			return None
		earliest_succ_end = _add_days(pred.get("end"), lag)
		return _add_days(earliest_succ_end, -succ_dur)
	return None


def _compute_earliest_start(task_id, tasks_by_id, edges):
	"""MAX (most binding) earliest-start over all predecessor edges.
	Returns (date, reason) or (None, None) when unconstrained."""
	succ = tasks_by_id.get(task_id)
	if not succ:
		return None, None
	best_date = None
	best_reason = None
	for dep in edges:
		if dep["successor"] != task_id:
			continue
		pred = tasks_by_id.get(dep["predecessor"])
		if not pred:
			continue
		earliest = _earliest_start_for_edge(pred, succ, dep)
		if not earliest:
			continue
		if best_date is None or _diff_days(best_date, earliest) > 0:
			best_date = earliest
			best_reason = f"{dep['type']}, lag {dep.get('lag') or 0} from {dep['predecessor']}"
	return best_date, best_reason


def _downstream_subgraph(root_id, edges):
	subgraph = {root_id}
	stack = [root_id]
	while stack:
		node = stack.pop()
		for e in edges:
			if e["predecessor"] == node and e["successor"] not in subgraph:
				subgraph.add(e["successor"])
				stack.append(e["successor"])
	return subgraph


def _topological_downstream(root_id, edges):
	"""[root, ...successors] in topological order. If a cycle is present the
	returned order is SHORTER than the subgraph (caller aborts)."""
	subgraph = _downstream_subgraph(root_id, edges)
	indeg = {i: 0 for i in subgraph}
	for d in edges:
		if d["predecessor"] in subgraph and d["successor"] in subgraph:
			indeg[d["successor"]] = indeg.get(d["successor"], 0) + 1
	queue = [i for i, deg in indeg.items() if deg == 0]
	order = []
	while queue:
		node = queue.pop(0)
		order.append(node)
		for e in edges:
			if e["predecessor"] == node and e["successor"] in subgraph:
				indeg[e["successor"]] -= 1
				if indeg[e["successor"]] == 0:
					queue.append(e["successor"])
	return order, len(subgraph)


def compute_conflicts(root_id, tasks_by_id, edges):
	"""FLAG-ONLY: {task_id: (conflict_bool, reason)} for the downstream subgraph.
	Never moves dates. Milestone anchor = end; Activity/Inspection anchor = start.
	Inspection gate: a predecessor Inspection not Completed flags the successor."""
	result = {}
	for tid in _downstream_subgraph(root_id, edges):
		task = tasks_by_id.get(tid)
		if not task:
			continue
		is_ms = task.get("type") == "Milestone"
		anchor = task.get("end") if is_ms else task.get("start")
		earliest, reason = _compute_earliest_start(tid, tasks_by_id, edges)
		conflict = False
		conflict_reason = ""
		if earliest and anchor and _diff_days(anchor, earliest) > 0:
			conflict = True
			days = _diff_days(anchor, earliest)
			which = "Due" if is_ms else "Starts"
			conflict_reason = f"{which} {days} day{'' if days == 1 else 's'} earlier than allowed ({reason})."

		incomplete_inspection = None
		for d in edges:
			if d["successor"] != tid:
				continue
			pred = tasks_by_id.get(d["predecessor"])
			if pred and pred.get("type") == "Inspection" and pred.get("status") != "Completed":
				incomplete_inspection = pred
				break
		if incomplete_inspection:
			conflict = True
			ins_reason = f"Waiting on inspection {incomplete_inspection['name']} ({incomplete_inspection.get('status')})."
			conflict_reason = f"{ins_reason} {conflict_reason}" if conflict_reason else ins_reason

		result[tid] = (conflict, conflict_reason)
	return result


def compute_cascade(root_id, tasks_by_id, edges, root_override=None):
	"""CASCADE: duration-preserving forward shifts in topological order. Never
	pulls earlier (slack preserved). `root_override` = {"start","end"} sets the
	root's working dates (the user's move) without persisting. Returns moves[] or
	None on a cycle."""
	order, size = _topological_downstream(root_id, edges)
	if len(order) != size:
		return None  # cycle

	working = {}
	for tid in order:
		t = tasks_by_id.get(tid)
		if not t:
			continue
		is_ms = t.get("type") == "Milestone"
		start = t.get("start")
		end = t.get("end")
		if tid == root_id and root_override:
			start = root_override.get("start")
			end = root_override.get("end")
		working[tid] = {
			"start": start,
			"end": end,
			"dur": 0 if is_ms else _diff_days(start, end),
			"is_ms": is_ms,
			"type": t.get("type"),
		}

	moves = []
	for tid in order:
		if tid == root_id:
			continue
		cur = working.get(tid)
		if not cur:
			continue
		if cur["is_ms"]:
			if not cur["end"]:
				continue
		elif not cur["start"] or not cur["end"]:
			continue

		binding = None
		binding_reason = None
		for dep in edges:
			if dep["successor"] != tid:
				continue
			pd = working.get(dep["predecessor"])
			if pd is None:
				t = tasks_by_id.get(dep["predecessor"])
				pd = {"start": t.get("start"), "end": t.get("end"), "type": t.get("type")} if t else None
			if not pd or not pd.get("end"):
				continue
			pred = {"start": pd.get("start"), "end": pd.get("end"), "type": pd.get("type")}
			succ = {"start": cur["start"], "end": cur["end"], "type": cur["type"]}
			earliest = _earliest_start_for_edge(pred, succ, dep, cur["dur"])
			if not earliest:
				continue
			if binding is None or _diff_days(binding, earliest) > 0:
				binding = earliest
				binding_reason = f"{dep['type']}, lag {dep.get('lag') or 0} from {dep['predecessor']}"

		if not binding:
			continue
		anchor = cur["end"] if cur["is_ms"] else cur["start"]
		if _diff_days(anchor, binding) > 0:
			if cur["is_ms"]:
				moves.append(
					{
						"task": tid,
						"old_start": None,
						"old_end": _iso(cur["end"]),
						"new_start": None,
						"new_end": _iso(binding),
						"reason": binding_reason,
						"is_milestone": True,
					}
				)
				working[tid] = {**cur, "end": binding}
			else:
				new_end = _add_days(binding, cur["dur"])
				moves.append(
					{
						"task": tid,
						"old_start": _iso(cur["start"]),
						"old_end": _iso(cur["end"]),
						"new_start": _iso(binding),
						"new_end": _iso(new_end),
						"reason": binding_reason,
					}
				)
				working[tid] = {**cur, "start": binding, "end": new_end}
	return moves


# --- frappe bindings: load graph, persist flags, recompute, reschedule --------


def _load_graph(project):
	tasks = frappe.get_all(
		"Task",
		filters={"project": project},
		fields=["name", "type", "exp_start_date", "exp_end_date", "status"],
		limit_page_length=0,
	)
	tasks_by_id = {}
	for t in tasks:
		tasks_by_id[t.name] = {
			"name": t.name,
			"type": t.type or "Activity",
			"start": getdate(t.exp_start_date) if t.exp_start_date else None,
			"end": getdate(t.exp_end_date) if t.exp_end_date else None,
			"status": t.status,
		}
	names = list(tasks_by_id.keys())
	edges = []
	if names:
		rows = frappe.get_all(
			"Task Depends On",
			filters={"parent": ["in", names], "parenttype": "Task"},
			fields=["parent", "task", "dependency_type", "lag_days"],
		)
		for r in rows:
			# Only edges whose predecessor is also in this project's set.
			if r.task in tasks_by_id:
				edges.append(
					{
						"predecessor": r.task,
						"successor": r.parent,
						"type": r.dependency_type or "FS",
						"lag": r.lag_days or 0,
					}
				)
	return tasks_by_id, edges


def _set_conflict(name, conflict, reason):
	cur = frappe.db.get_value("Task", name, ["schedule_conflict", "conflict_reason"], as_dict=True)
	if not cur:
		return
	new_flag = 1 if conflict else 0
	if (cur.schedule_conflict or 0) != new_flag or (cur.conflict_reason or "") != (reason or ""):
		# Direct write — no doc events, so this never re-triggers the on_update hook.
		frappe.db.set_value(
			"Task",
			name,
			{"schedule_conflict": new_flag, "conflict_reason": reason or ""},
			update_modified=False,
		)


def recompute_schedule_conflicts(root_task):
	"""Recompute + persist schedule_conflict/conflict_reason for root_task and its
	downstream subgraph. Cheap when the task has no dependency edges."""
	if not root_task:
		return
	# Fast path: a task in no edge can never conflict — just clear its own flag.
	in_edge = frappe.db.exists("Task Depends On", {"parent": root_task, "parenttype": "Task"})
	is_pred = frappe.db.exists("Task Depends On", {"task": root_task, "parenttype": "Task"})
	if not in_edge and not is_pred:
		_set_conflict(root_task, False, "")
		return
	project = frappe.db.get_value("Task", root_task, "project")
	if not project:
		return
	tasks_by_id, edges = _load_graph(project)
	for tid, (conflict, reason) in compute_conflicts(root_task, tasks_by_id, edges).items():
		_set_conflict(tid, conflict, reason)


def recompute_conflicts_on_update(doc, method=None):
	"""Task on_update hook — re-flag this task's downstream subgraph. Skipped
	during a cascade commit (the cascade re-flags once at the end)."""
	if frappe.flags.get("in_schedule_cascade"):
		return
	recompute_schedule_conflicts(doc.name)


@frappe.whitelist()
def reschedule_downstream(task, new_start=None, new_end=None, dry_run=1):
	"""Preview (dry_run=1) or commit (dry_run=0) a duration-preserving downstream
	cascade after moving `task` to new_start/new_end. Returns {"moves": [...]}.

	Commit writes each affected task via doc.save(), so Task write permission is
	enforced per task and the stage-sync / progress hooks still run; conflict
	re-flagging is suppressed per-save and done once at the end.
	"""
	dry_run = int(dry_run)
	if not task:
		frappe.throw(_("task is required"))
	root = frappe.get_doc("Task", task)
	tasks_by_id, edges = _load_graph(root.project)
	if task not in tasks_by_id:
		frappe.throw(_("Task is not part of a project schedule."))

	root_override = None
	if new_start or new_end:
		root_override = {
			"start": getdate(new_start) if new_start else None,
			"end": getdate(new_end) if new_end else None,
		}

	moves = compute_cascade(task, tasks_by_id, edges, root_override)
	if moves is None:
		frappe.throw(_("Cycle detected in the downstream schedule — cascade aborted."))

	if dry_run:
		return {"moves": moves}

	frappe.flags.in_schedule_cascade = True
	try:
		if root_override:
			if root_override.get("start") is not None:
				root.exp_start_date = root_override["start"]
			if root_override.get("end") is not None:
				root.exp_end_date = root_override["end"]
			root.save()
		for m in moves:
			t = frappe.get_doc("Task", m["task"])
			if m.get("is_milestone"):
				# normalize_milestone_task collapses start to end on save.
				t.exp_end_date = m["new_end"]
			else:
				t.exp_start_date = m["new_start"]
				t.exp_end_date = m["new_end"]
			t.save()
	finally:
		frappe.flags.in_schedule_cascade = False

	recompute_schedule_conflicts(task)
	return {"moves": moves}
