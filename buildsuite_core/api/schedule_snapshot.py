# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Schedule snapshots — the shared state layer behind schedule **undo** and
**revisions**.

A snapshot is a serialized copy of a project's task dates (`exp_start_date` /
`exp_end_date`). Two kinds:

- **Undo** — captured automatically right before a *group* action (a downstream
  cascade) mutates several tasks. `undo_last` pops the newest Undo snapshot and
  restores it, so repeated undo walks the stack back. The stack is bounded per
  project (`UNDO_LIMIT`); older Undo snapshots auto-prune.
- **Revision** — a named, user-saved restore point. `save_revision` captures one;
  `restore_snapshot` restores it (capturing an Undo first, so a restore is itself
  undoable).

Restore writes each task's dates back via `doc.save()` (so per-Task write perms
and the progress/stage hooks still run), suppressing per-save conflict re-flagging
via the `in_schedule_cascade` flag and recomputing conflicts once at the end —
the same machinery `reschedule_downstream` uses.
"""

import json

import frappe
from frappe import _
from frappe.utils import getdate

SNAPSHOT = "Schedule Snapshot"
UNDO_LIMIT = 10


# --- capture --------------------------------------------------------------


def _serialize_schedule(project):
	"""Every task in the project with its scheduling dates (ISO strings)."""
	tasks = frappe.get_all(
		"Task",
		filters={"project": project},
		fields=["name", "exp_start_date", "exp_end_date"],
	)
	return [
		{
			"task": t.name,
			"exp_start_date": str(t.exp_start_date) if t.exp_start_date else None,
			"exp_end_date": str(t.exp_end_date) if t.exp_end_date else None,
		}
		for t in tasks
	]


def _default_label(kind, trigger, root_task):
	if kind == "Undo" and root_task:
		return f"Before cascade from {root_task}"
	if kind == "Undo":
		return "Before schedule change"
	return "Revision"


def capture_snapshot(project, kind, label=None, trigger=None, root_task=None):
	"""Serialize the project schedule into a Schedule Snapshot. Internal — callers
	are already permitted to change the schedule (or are the cascade itself), so the
	insert runs with ignore_permissions. Undo snapshots prune to the last UNDO_LIMIT."""
	rows = _serialize_schedule(project)
	doc = frappe.get_doc(
		{
			"doctype": SNAPSHOT,
			"project": project,
			"kind": kind,
			"label": label or _default_label(kind, trigger, root_task),
			"trigger": trigger,
			"root_task": root_task,
			"task_count": len(rows),
			"snapshot_data": json.dumps(rows),
		}
	).insert(ignore_permissions=True)
	if kind == "Undo":
		_prune_undo_stack(project)
	return doc.name


def _prune_undo_stack(project):
	names = frappe.get_all(
		SNAPSHOT,
		filters={"project": project, "kind": "Undo"},
		order_by="creation desc",
		pluck="name",
	)
	for name in names[UNDO_LIMIT:]:
		frappe.delete_doc(SNAPSHOT, name, force=True, ignore_permissions=True)


# --- restore --------------------------------------------------------------


def _apply_snapshot(rows):
	"""Write the saved dates back to each task. Returns the list of changed task
	names. Runs under in_schedule_cascade so per-save conflict re-flagging is
	suppressed; the caller recomputes conflicts once afterwards. Each doc.save()
	enforces per-Task write permission."""
	changed = []
	frappe.flags.in_schedule_cascade = True
	try:
		for r in rows:
			name = r.get("task")
			if not name or not frappe.db.exists("Task", name):
				continue
			new_start = getdate(r["exp_start_date"]) if r.get("exp_start_date") else None
			new_end = getdate(r["exp_end_date"]) if r.get("exp_end_date") else None
			t = frappe.get_doc("Task", name)
			if t.exp_start_date == new_start and t.exp_end_date == new_end:
				continue
			t.exp_start_date = new_start
			t.exp_end_date = new_end
			t.save()
			changed.append(name)
	finally:
		frappe.flags.in_schedule_cascade = False

	# Re-flag conflicts across the tasks we touched (idempotent per subgraph).
	from buildsuite_core.api.schedule_engine import recompute_schedule_conflicts

	for name in changed:
		recompute_schedule_conflicts(name)
	return changed


@frappe.whitelist()
def restore_snapshot(name: str, capture_undo: int = 1):
	"""Restore a snapshot's dates. Captures an Undo of the current state first (so
	the restore is itself undoable) unless capture_undo=0."""
	doc = frappe.get_doc(SNAPSHOT, name)
	if not frappe.has_permission("Project", "read", doc.project):
		frappe.throw(_("You are not permitted to restore this schedule."), frappe.PermissionError)
	rows = json.loads(doc.snapshot_data or "[]")
	if int(capture_undo):
		capture_snapshot(
			doc.project, "Undo", label=f"Before restoring {doc.label or name}", trigger="restore_snapshot"
		)
	changed = _apply_snapshot(rows)
	return {"restored": name, "changed": len(changed)}


@frappe.whitelist()
def undo_last(project: str):
	"""Pop the newest Undo snapshot for the project, restore it, and delete it — so
	repeated calls walk the stack back. No-op (undone=False) when the stack is empty."""
	latest = frappe.get_all(
		SNAPSHOT,
		filters={"project": project, "kind": "Undo"},
		order_by="creation desc",
		limit=1,
		pluck="name",
	)
	if not latest:
		return {"undone": False, "remaining": 0}
	snap = frappe.get_doc(SNAPSHOT, latest[0])
	if not frappe.has_permission("Project", "read", snap.project):
		frappe.throw(_("You are not permitted to undo on this schedule."), frappe.PermissionError)
	rows = json.loads(snap.snapshot_data or "[]")
	changed = _apply_snapshot(rows)
	frappe.delete_doc(SNAPSHOT, snap.name, force=True, ignore_permissions=True)
	remaining = frappe.db.count(SNAPSHOT, {"project": project, "kind": "Undo"})
	return {"undone": True, "changed": len(changed), "label": snap.label, "remaining": remaining}


# --- revisions ------------------------------------------------------------


@frappe.whitelist()
def save_revision(project: str, label: str):
	"""Save a named Revision snapshot of the project's current schedule."""
	if not frappe.has_permission("Project", "read", project):
		frappe.throw(_("You are not permitted to snapshot this schedule."), frappe.PermissionError)
	if not (label or "").strip():
		frappe.throw(_("A revision label is required."))
	name = capture_snapshot(project, "Revision", label=label.strip(), trigger="save_revision")
	return {"name": name}


@frappe.whitelist()
def list_snapshots(project: str, kind: str | None = None):
	"""Snapshots for a project (newest first). Pass kind to filter to Undo/Revision."""
	if not frappe.has_permission("Project", "read", project):
		frappe.throw(_("You are not permitted to view this schedule."), frappe.PermissionError)
	filters = {"project": project}
	if kind:
		filters["kind"] = kind
	return frappe.get_all(
		SNAPSHOT,
		filters=filters,
		fields=["name", "kind", "label", "trigger", "root_task", "task_count", "creation", "owner"],
		order_by="creation desc",
	)


@frappe.whitelist()
def delete_snapshot(name: str):
	"""Delete a snapshot (enforces the Schedule Snapshot delete permission)."""
	frappe.delete_doc(SNAPSHOT, name)
	return True
