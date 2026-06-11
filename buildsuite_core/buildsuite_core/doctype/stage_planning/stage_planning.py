# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow


class StagePlanning(Document):
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
