# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow
from frappe.utils import flt


class StagePlanning(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.stage_planning_dependency.stage_planning_dependency import (
			StagePlanningDependency,
		)
		from buildsuite_core.buildsuite_core.doctype.stage_planning_task.stage_planning_task import (
			StagePlanningTask,
		)

		dependencies: DF.Table[StagePlanningDependency]
		description: DF.Text | None
		planned_completion_pct: DF.Percent
		planned_end: DF.Date | None
		planned_start: DF.Date | None
		planned_task_count: DF.Int
		project: DF.Link
		reject_reason: DF.SmallText | None
		stage_name: DF.Data
		stage_planning_tasks: DF.Table[StagePlanningTask]
		workflow_state: DF.Link | None
	# end: auto-generated types

	def validate(self):
		# SAW-011 — an Approved stage is locked: its task list and planned
		# quantities can't change in place. The supported way to modify is Revise
		# (Approved -> Draft), which changes workflow_state and so isn't blocked
		# here. Editing a Rejected stage is no longer auto-flipped to Draft
		# (SAW-006) — the frontend clones it via revise_stage_planning() instead.
		if not self.is_new():
			before = self.get_doc_before_save()
			if (
				before
				and before.workflow_state == "Approved"
				and self.workflow_state == "Approved"
				and self._stage_tasks_changed(before)
			):
				frappe.throw(
					_(
						"An approved stage is locked. Revise it back to Draft to "
						"change tasks or planned quantities."
					)
				)

		# A stage can only land in Rejected with a reason on file. The Vue reject
		# popup and the reject_stage_planning() method below both supply it; this
		# guards any other path (e.g. a direct Desk workflow action).
		if self.workflow_state == "Rejected" and not (self.reject_reason or "").strip():
			frappe.throw(_("A rejection reason is required to reject this stage."))

		# Server-maintained aggregates for the list: real nested-task count + mean
		# task progress (the list derives status from mean_progress, not dates).
		task_names = [r.task for r in (self.stage_planning_tasks or []) if r.task]
		self.task_count, self.mean_progress = _stage_aggregates(task_names)

	def _stage_tasks_changed(self, before):
		"""Whether stage_planning_tasks differ from the persisted version — rows
		added/removed, or any task / planned_qty / qty_unit changed."""

		def snap(doc):
			return [(r.task, r.planned_qty, r.qty_unit) for r in (doc.stage_planning_tasks or [])]

		return snap(self) != snap(before)

	def on_update(self):
		# SAW-013 — record each workflow transition on the timeline. add_comment
		# stamps the acting user + timestamp. Captures submit / approve / reject /
		# revise / cancel whether driven by generic apply_workflow or our endpoints.
		before = self.get_doc_before_save()
		if not before:
			return
		old, new = before.workflow_state, self.workflow_state
		if old == new:
			return
		label = _stage_transition_label(old, new, self.reject_reason)
		if label:
			self.add_comment("Workflow", label)


def _stage_aggregates(task_names):
	"""(task_count, mean_progress) for member task names. Mean is the simple average
	of member task progress; (0, 0) when the stage has no tasks."""
	count = len(task_names)
	if not count:
		return 0, 0
	rows = frappe.get_all("Task", filters={"name": ["in", task_names]}, fields=["progress"])
	mean = sum(flt(r.progress) for r in rows) / len(rows) if rows else 0
	return count, round(mean)


def recompute_stage_aggregates(stage):
	"""Set task_count + mean_progress on a Stage Planning from its current child rows
	and member task progress, via db.set_value (no save) — safe to call from a Task
	hook when a member task's progress changes."""
	task_names = frappe.get_all(
		"Stage Planning Task",
		filters={"parent": stage, "parenttype": "Stage Planning"},
		pluck="task",
	)
	count, mean = _stage_aggregates([t for t in task_names if t])
	frappe.db.set_value(
		"Stage Planning", stage, {"task_count": count, "mean_progress": mean}, update_modified=False
	)


def _stage_transition_label(old, new, reason=None):
	if new == "Pending Approval":
		return _("Submitted for approval")
	if new == "Approved":
		return _("Approved")
	if new == "Rejected":
		r = (reason or "").strip()
		return _("Rejected") + (f": {r}" if r else "")
	if new == "Draft" and old == "Approved":
		return _("Revised — reopened to Draft")
	if new == "Cancelled":
		return _("Cancelled")
	return None


def _activity_type_from_content(content):
	c = (content or "").lower()
	if "submitt" in c:
		return "submitted"
	if "approv" in c:
		return "approved"
	if "reject" in c:
		return "rejected"
	if "revis" in c:
		return "revised"
	if "cancel" in c:
		return "cancelled"
	return "info"


@frappe.whitelist()
def reject_stage_planning(name: str, reason: str):
	"""Reject a Stage Planning with a mandatory reason.

	Stamps reject_reason and applies the "Reject" workflow transition in one
	save, so the reason and the Rejected state always land together. apply_workflow
	enforces that the calling user is allowed to perform the transition from the
	current state.
	"""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("A rejection reason is required."))

	# apply_workflow() re-fetches the doc and calls load_from_db(), so an in-memory
	# field set here would be discarded. Persist the reason to the column first, then
	# the reload inside apply_workflow picks it up and validate() passes.
	frappe.db.set_value("Stage Planning", name, "reject_reason", reason)
	doc = frappe.get_doc("Stage Planning", name)
	apply_workflow(doc, "Reject")
	return {
		"workflow_state": frappe.db.get_value("Stage Planning", name, "workflow_state"),
		"reject_reason": reason,
	}


@frappe.whitelist()
def add_stage_delay_reason(
	stage: str,
	reason: str,
	responsible_party: str | None = None,
	days_delayed: str | None = None,
	note: str | None = None,
):
	"""Append a delay-log row to a Stage Planning.

	Logging a delay is NOT a stage edit — it must work in any workflow state,
	including Approved (which the workflow locks for editing). So we gate on
	project access (read permission resolves project membership) and save with
	ignore_permissions, rather than the stage's write/edit lock. No state change
	occurs, so the workflow transition validation is not triggered.
	"""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("A delay reason is required."))

	doc = frappe.get_doc("Stage Planning", stage)
	if not doc.has_permission("read"):
		frappe.throw(_("You do not have access to this stage."), frappe.PermissionError)

	try:
		days = int(days_delayed)
	except (TypeError, ValueError):
		days = None

	row = doc.append(
		"delay_reasons",
		{
			"reason": reason,
			"responsible_party": responsible_party or None,
			"days_delayed": days,
			"note": (note or "").strip() or None,
			"logged_by": frappe.session.user,
			"logged_on": frappe.utils.now_datetime(),
		},
	)
	doc.save(ignore_permissions=True)
	return row.as_dict()


@frappe.whitelist()
def revise_stage_planning(name: str):
	"""SAW-006 — clone a Rejected stage into a fresh Draft.

	The original Rejected stage is left untouched as an audit record. The clone
	carries the stage_planning_tasks + dependencies child rows, starts in Draft
	with no rejection reason and an empty delay log. Returns the clone's name so
	the frontend can open it in edit mode.
	"""
	source = frappe.get_doc("Stage Planning", name)
	if not source.has_permission("read"):
		frappe.throw(_("You do not have access to this stage."), frappe.PermissionError)

	clone = frappe.copy_doc(source)
	clone.workflow_state = "Draft"
	clone.reject_reason = None
	clone.delay_reasons = []
	clone.insert()
	clone.add_comment("Info", _("Revised from rejected stage {0}").format(name))
	return {"name": clone.name}


@frappe.whitelist()
def get_stage_activity(name: str):
	"""SAW-013 — normalized activity feed: creation + workflow timeline comments,
	oldest first. Shape matches the frontend Activity panel."""
	doc = frappe.get_doc("Stage Planning", name)
	if not doc.has_permission("read"):
		frappe.throw(_("You do not have access to this stage."), frappe.PermissionError)

	def user_name(user):
		return frappe.db.get_value("User", user, "full_name") or user

	entries = [
		{
			"type": "created",
			"by": doc.owner,
			"by_name": user_name(doc.owner),
			"at": str(doc.creation),
			"text": _("Created"),
		}
	]

	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Stage Planning",
			"reference_name": name,
			"comment_type": ["in", ["Workflow", "Info"]],
		},
		fields=["owner", "creation", "content"],
		order_by="creation asc",
	)
	for c in comments:
		text = frappe.utils.strip_html(c.content or "").strip()
		entries.append(
			{
				"type": _activity_type_from_content(text),
				"by": c.owner,
				"by_name": user_name(c.owner),
				"at": str(c.creation),
				"text": text,
			}
		)

	entries.sort(key=lambda e: e["at"])
	return entries
