# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Amending a cancelled document, as Desk does it."""

import frappe
from frappe.model.workflow import get_workflow_name


def amended_copy(src):
	"""A new draft copy of the cancelled `src`, linked to it by `amended_from` (not inserted).

	Its workflow state starts again at the workflow's first draft state, as Desk's amend does
	(frappe.ui.form.States.set_default_state). A copy keeps the original's "Cancelled", and Frappe
	refuses a new document in that state ("Workflow State transition not allowed from Draft to
	Cancelled")."""
	amended = frappe.copy_doc(src)
	amended.amended_from = src.name
	amended.docstatus = 0
	workflow = get_workflow_name(src.doctype)
	if workflow:
		wf = frappe.get_cached_doc("Workflow", workflow)
		first_draft = next((s.state for s in wf.states if str(s.doc_status) == "0"), None)
		amended.set(wf.workflow_state_field or "workflow_state", first_draft)
	return amended
