# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Generic Frappe-Workflow bridge for the Vue app.

The finance documents (Sales Invoice, Purchase Invoice, Subcontractor Bill) ship with a
plain docstatus lifecycle: the detail views drive Submit / Cancel directly. If a site
later configures an *active* Frappe Workflow for one of those doctypes, the UI should
defer to the workflow instead — showing exactly the transitions the signed-in user may
take from the document's current state, and applying them through Frappe's engine.

This module is the seam. It exposes two thin, doctype-agnostic endpoints:

  · get_workflow_info(doctype[, name]) — is an active workflow configured, and (given a
    doc) what state is it in + which transitions can THIS user take. Frappe already filters
    transitions by the user's roles and each transition's condition, so persona-derived
    roles (see utils/user.sync_persona_roles) gate the buttons natively — no persona field
    on Workflow is needed.
  · apply_action(doctype, name, action) — run one workflow action via Frappe, return the
    resulting lifecycle snapshot.

When no workflow is configured, get_workflow_info reports active=False and callers keep
their existing docstatus buttons; nothing else changes.
"""

import frappe
from frappe.model.workflow import apply_workflow, get_transitions, get_workflow, get_workflow_name


def _state_field(doctype):
	"""The workflow_state field name for `doctype`'s active workflow, or None."""
	name = get_workflow_name(doctype)
	if not name:
		return None
	return get_workflow(doctype).workflow_state_field


@frappe.whitelist()
def get_workflow_info(doctype: str, name: str | None = None):
	"""Whether an active workflow governs `doctype`; with `name`, also the doc's current
	state and the transitions available to the calling user (role + condition filtered)."""
	wf_name = get_workflow_name(doctype)
	info = {
		"active": bool(wf_name),
		"workflow": wf_name or None,
		"state_field": None,
		"state": None,
		"transitions": [],
	}
	if not wf_name:
		return info

	workflow = get_workflow(doctype)
	info["state_field"] = workflow.workflow_state_field

	if name:
		doc = frappe.get_doc(doctype, name)
		doc.check_permission("read")
		info["state"] = doc.get(workflow.workflow_state_field)
		info["transitions"] = [
			{
				"action": t.get("action"),
				"next_state": t.get("next_state"),
				"allowed": t.get("allowed"),
			}
			for t in get_transitions(doc, workflow)
		]
	return info


@frappe.whitelist()
def apply_action(doctype: str, name: str, action: str):
	"""Apply a workflow `action` to (doctype, name) through Frappe's engine, then return
	the new lifecycle snapshot. Frappe enforces the transition's role, condition and
	self-approval rules, and drives docstatus when the target state is submitted/cancelled."""
	doc = frappe.get_doc(doctype, name)
	updated = apply_workflow(doc.as_dict(), action)
	state_field = _state_field(doctype)
	return {
		"name": updated.name,
		"state": updated.get(state_field) if state_field else None,
		"docstatus": updated.docstatus,
	}


def workflow_active(doctype):
	"""Helper for server-side guards: True when an active workflow governs `doctype`."""
	return bool(get_workflow_name(doctype))
