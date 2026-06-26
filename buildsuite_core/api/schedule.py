"""Schedule graph API for the Gantt + the dependency cycle guard.

Dependencies are stored on ERPNext's native Task.depends_on child table, whose
`task` field is the PREDECESSOR, enriched with custom fields dependency_type
(FS/SS/FF) and lag_days (Slice 1.1 Bit 1). Successors are inferred (reverse the
edge set), never stored. See context/scheduler-gantt-plan.md.
"""

import frappe
from frappe import _


def incomplete_fs_predecessor(task_name, depends_on_rows=None):
	"""Name of a Finish-to-Start predecessor of `task_name` that isn't Completed yet
	(and therefore blocks the successor from starting), or None.

	Only FS edges gate (a start can't precede the predecessor's finish). A negative lag
	is a lead — overlap is intended — so those edges don't block. `depends_on_rows`
	lets callers pass an unsaved doc's in-memory child table; otherwise rows are read
	from the DB. Predecessor "done" is its BuildSuite task_status == "Completed".
	"""
	if depends_on_rows is None:
		if not task_name:
			return None
		depends_on_rows = frappe.get_all(
			"Task Depends On",
			filters={"parent": task_name, "parenttype": "Task"},
			fields=["task", "dependency_type", "lag_days"],
		)
	for row in depends_on_rows:
		if (row.get("dependency_type") or "FS") != "FS":
			continue
		if int(row.get("lag_days") or 0) < 0:
			continue
		pred = row.get("task")
		if pred and frappe.db.get_value("Task", pred, "task_status") != "Completed":
			return pred
	return None


@frappe.whitelist()
def get_project_schedule(project: str):
	"""Return the schedule graph for a project: every task with its scheduling
	fields and its PREDECESSOR edges. Successors are inferred client-side by
	reversing the edge set. Respects Task read permission (uses get_list).
	"""
	if not project:
		frappe.throw(_("project is required"))

	tasks = frappe.get_list(
		"Task",
		filters={"project": project},
		fields=[
			"name",
			"subject",
			"type as task_type",
			"task_status",
			"exp_start_date",
			"exp_end_date",
			"progress",
			"work_package",
			"project",
			"owner",
			"schedule_conflict",
			"conflict_reason",
		],
		order_by="exp_start_date asc, creation asc",
		limit_page_length=0,
	)

	task_names = [t.name for t in tasks]
	for t in tasks:
		t["predecessors"] = []

	if task_names:
		by_name = {t.name: t for t in tasks}
		edges = frappe.get_all(
			"Task Depends On",
			filters={"parent": ["in", task_names], "parenttype": "Task"},
			fields=["parent", "task as predecessor", "dependency_type", "lag_days"],
		)
		for e in edges:
			parent = by_name.get(e.parent)
			# Only attach edges whose predecessor is also in this project's set;
			# cross-project edges are out of scope for the single-project Gantt.
			if parent is not None and e.predecessor in by_name:
				parent["predecessors"].append(
					{
						"task": e.predecessor,
						"dependency_type": e.dependency_type or "FS",
						"lag_days": e.lag_days or 0,
					}
				)

	# Grouping metadata for the Gantt's By-WP / By-Stage axes.
	work_packages = frappe.get_all(
		"Work Package",
		filters={"project": project},
		fields=["name", "work_package_name"],
		order_by="creation asc",
	)
	stages = frappe.get_all(
		"Stage Planning",
		filters={"project": project},
		fields=["name", "stage_name", "planned_start", "planned_end"],
		order_by="planned_start asc, creation asc",
	)
	if stages:
		members = frappe.get_all(
			"Stage Planning Task",
			filters={"parent": ["in", [s.name for s in stages]], "parenttype": "Stage Planning"},
			fields=["parent", "task"],
		)
		by_stage = {}
		for m in members:
			by_stage.setdefault(m.parent, []).append(m.task)
		for s in stages:
			s["tasks"] = by_stage.get(s.name, [])

	# Project name + boundary dates for the Gantt's project start/end band.
	proj = (
		frappe.db.get_value(
			"Project", project, ["project_name", "expected_start_date", "expected_end_date"], as_dict=True
		)
		or {}
	)

	return {
		"project": project,
		"project_name": proj.get("project_name") or project,
		"project_start": proj.get("expected_start_date"),
		"project_end": proj.get("expected_end_date"),
		"tasks": tasks,
		"work_packages": work_packages,
		"stages": stages,
	}


# --- single-task dependency CRUD (for the Task Detail "Dependencies" section) --


@frappe.whitelist()
def get_task_dependencies(task: str):
	"""Predecessors (this task's depends_on) + inferred successors (tasks whose
	depends_on includes this task), each with subject + dependency_type + lag."""
	if not task:
		frappe.throw(_("task is required"))

	predecessors = frappe.get_all(
		"Task Depends On",
		filters={"parent": task, "parenttype": "Task"},
		fields=["task", "dependency_type", "lag_days"],
	)
	successors = frappe.get_all(
		"Task Depends On",
		filters={"task": task, "parenttype": "Task"},
		fields=["parent as task", "dependency_type", "lag_days"],
	)

	ids = list({r.task for r in predecessors} | {r.task for r in successors})
	subjects = {}
	if ids:
		for row in frappe.get_all("Task", filters={"name": ["in", ids]}, fields=["name", "subject"]):
			subjects[row.name] = row.subject
	for r in predecessors + successors:
		r["subject"] = subjects.get(r.task, r.task)
		r["dependency_type"] = r.dependency_type or "FS"
		r["lag_days"] = r.lag_days or 0

	return {"predecessors": predecessors, "successors": successors}


@frappe.whitelist()
def add_task_predecessor(task: str, predecessor: str, dependency_type: str = "FS", lag_days: int = 0):
	"""Add (or update) a predecessor edge on `task`. Saves the Task, so the
	cycle guard runs and a circular edge is rejected. Returns the fresh graph."""
	if not task or not predecessor:
		frappe.throw(_("task and predecessor are required"))
	if task == predecessor:
		frappe.throw(_("A task cannot depend on itself."))

	doc = frappe.get_doc("Task", task)
	for row in doc.depends_on:
		if row.task == predecessor:
			row.dependency_type = dependency_type or "FS"
			row.lag_days = int(lag_days or 0)
			break
	else:
		doc.append(
			"depends_on",
			{
				"task": predecessor,
				"dependency_type": dependency_type or "FS",
				"lag_days": int(lag_days or 0),
			},
		)
	doc.save()
	return get_task_dependencies(task)


@frappe.whitelist()
def remove_task_predecessor(task: str, predecessor: str):
	"""Remove a predecessor edge from `task`. Returns the fresh graph."""
	if not task or not predecessor:
		frappe.throw(_("task and predecessor are required"))
	doc = frappe.get_doc("Task", task)
	doc.set("depends_on", [r for r in doc.depends_on if r.task != predecessor])
	doc.save()
	return get_task_dependencies(task)


# --- milestone normalization --------------------------------------------------


def normalize_milestone_task(doc, method=None):
	"""A Milestone is a point in time (zero-duration) — collapse its dates to a
	single day so the engine + Gantt render it as a diamond, not a bar.

	Scheduling type now lives on the native `type` Link (-> Task Type master)."""
	if getattr(doc, "type", None) != "Milestone":
		return
	if doc.exp_start_date:
		doc.exp_end_date = doc.exp_start_date
	elif doc.exp_end_date:
		doc.exp_start_date = doc.exp_end_date


# --- cycle guard --------------------------------------------------------------


def validate_task_dependencies(doc, method=None):
	"""Task validate hook: reject a depends_on edge that would create a cycle
	(a task depending, transitively, on itself)."""
	for row in doc.depends_on or []:
		predecessor = row.task
		if not predecessor:
			continue
		if predecessor == doc.name:
			frappe.throw(_("A task cannot depend on itself."))
		if _creates_cycle(doc.name, predecessor):
			frappe.throw(_("Dependency on {0} would create a circular schedule.").format(predecessor))


def _creates_cycle(task_name, predecessor_name, _seen=None):
	"""True if `task_name` is already a (transitive) predecessor of
	`predecessor_name` — so adding the edge predecessor_name -> task_name closes a
	loop. Walks UP the depends_on graph from predecessor_name over stored edges.
	"""
	if not task_name or not predecessor_name:
		return False
	if predecessor_name == task_name:
		return True
	if _seen is None:
		_seen = set()
	if predecessor_name in _seen:
		return False
	_seen.add(predecessor_name)

	upstream = frappe.get_all(
		"Task Depends On",
		filters={"parent": predecessor_name, "parenttype": "Task"},
		pluck="task",
	)
	for p in upstream:
		if _creates_cycle(task_name, p, _seen):
			return True
	return False
