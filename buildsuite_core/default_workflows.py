# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Opt-in approval workflows for the submittable finance + procurement documents.

The always-on approval flows (Material Request, Scope Change Order, Stage Planning) ship as JSON
fixtures. These finance/procurement ones ship the SAME five-state lifecycle
(Draft → Pending Approval → Approved / Rejected, + Cancel) but INACTIVE (is_active=0), so a site
opts into approval by enabling the workflow in the Workflow list.

They are therefore seeded here (create-if-missing) rather than as fixtures: a fixture re-syncs on
every migrate and would reset an admin's is_active back to 0, undoing their opt-in. This seeder
never touches a workflow that already exists.

The generic Vue bridge (api.workflow + useWorkflow) and each doctype's submit/cancel guard already
defer to an active workflow, so enabling one immediately drives the buttons — nothing else to wire.
"""

import frappe

# (state, doc_status). Mirrors the shipped fixtures' lifecycle.
_STATES = [
	("Draft", "0"),
	("Pending Approval", "0"),
	("Approved", "1"),
	("Rejected", "0"),
	("Cancelled", "2"),
]

# (from_state, action, next_state) — one row per allowed role is generated from this.
_TRANSITIONS = [
	("Draft", "Submit for Approval", "Pending Approval"),
	("Pending Approval", "Approve", "Approved"),
	("Pending Approval", "Reject", "Rejected"),
	("Rejected", "Revise", "Draft"),
	("Approved", "Cancel", "Cancelled"),
]

_ACTIONS = ["Submit for Approval", "Approve", "Reject", "Revise", "Cancel"]

# document_type -> roles that may act. Sensible defaults keyed to who owns each document; an admin
# tunes them before/after enabling. Roles that don't exist on a site are skipped.
_WORKFLOW_ROLES = {
	"Purchase Invoice": [
		"BuildSuite Accountant",
		"BuildSuite PM",
		"BuildSuite Administrator",
		"System Manager",
	],
	"Sales Invoice": [
		"BuildSuite Accountant",
		"BuildSuite PM",
		"BuildSuite Administrator",
		"System Manager",
	],
	"Subcontractor Bill": [
		"BuildSuite QS",
		"BuildSuite PM",
		"BuildSuite Accountant",
		"BuildSuite Administrator",
		"System Manager",
	],
	"Purchase Order": [
		"BuildSuite Procurement Officer",
		"BuildSuite PM",
		"BuildSuite Administrator",
		"System Manager",
	],
	"Purchase Receipt": [
		"BuildSuite Store Keeper",
		"BuildSuite Procurement Officer",
		"BuildSuite Administrator",
		"System Manager",
	],
}


def _ensure_masters():
	"""The shared Workflow State + Workflow Action Master records the workflows reference. Shipped
	as fixtures too, but seeded here so this works on a site that never loaded them."""
	for state, _ in _STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state}
			).insert(ignore_permissions=True)
	for action in _ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc(
				{"doctype": "Workflow Action Master", "workflow_action_name": action}
			).insert(ignore_permissions=True)


def _build_workflow(doctype, roles):
	name = f"{doctype} Approval"
	wf = frappe.new_doc("Workflow")
	wf.workflow_name = name
	wf.document_type = doctype
	wf.is_active = 0  # opt-in — the admin enables approval per site
	wf.override_status = 0
	wf.send_email_alert = 0
	wf.workflow_state_field = "workflow_state"
	for state, doc_status in _STATES:
		wf.append(
			"states",
			{
				"state": state,
				"doc_status": doc_status,
				# allow_edit is a single role; the primary owner keeps the doc editable in the
				# working states, an admin owns the terminal ones.
				"allow_edit": "System Manager" if doc_status in ("1", "2") else roles[0],
				"is_optional_state": 1 if state == "Cancelled" else 0,
			},
		)
	for from_state, action, next_state in _TRANSITIONS:
		for role in roles:
			wf.append(
				"transitions",
				{
					"state": from_state,
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"allow_self_approval": 1,
					"condition": "",
				},
			)
	wf.flags.ignore_permissions = True
	wf.insert()
	return name


def seed_default_workflows():
	"""Create the opt-in (is_active=0) approval workflows if absent. Idempotent and
	non-clobbering: skips any doctype that already has a workflow, so an admin's activation is
	never reset."""
	_ensure_masters()
	created = []
	for doctype, roles in _WORKFLOW_ROLES.items():
		name = f"{doctype} Approval"
		# Never touch an existing workflow (ours or an admin's) for this doctype.
		if frappe.db.exists("Workflow", name) or frappe.db.exists("Workflow", {"document_type": doctype}):
			continue
		roles = [r for r in roles if frappe.db.exists("Role", r)]
		if not roles:
			continue
		created.append(_build_workflow(doctype, roles))
	return created
