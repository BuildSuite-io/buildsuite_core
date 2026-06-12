# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow


class StagePlanning(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.stage_planning_dependency.stage_planning_dependency import StagePlanningDependency
		from buildsuite_core.buildsuite_core.doctype.stage_planning_task.stage_planning_task import StagePlanningTask
		from frappe.types import DF

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
		# A stage can only land in Rejected with a reason on file. The Vue reject
		# popup and the reject_stage_planning() method below both supply it; this
		# guards any other path (e.g. a direct Desk workflow action).
		if self.workflow_state == "Rejected" and not (self.reject_reason or "").strip():
			frappe.throw(_("A rejection reason is required to reject this stage."))


@frappe.whitelist()
def reject_stage_planning(name, reason):
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
def add_stage_delay_reason(stage, reason, responsible_party=None, days_delayed=None, note=None):
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
