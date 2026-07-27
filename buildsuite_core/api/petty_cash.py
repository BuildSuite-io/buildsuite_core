# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Petty Cash Request — the live part of the Project Finance
workspace. Request → Disburse (posts a Journal Entry) → optionally reverse. Disbursing is
gated to the finance approver roles."""

import frappe
from frappe import _
from frappe.utils import flt

DOCTYPE = "Petty Cash Request"


def _can_disburse():
	from buildsuite_core.permissions.setup import PETTY_CASH_DISBURSE_ROLES

	return bool(set(frappe.get_roles()) & set(PETTY_CASH_DISBURSE_ROLES))


def _serialize(doc):
	comments = frappe.get_all(
		"Comment",
		filters={"reference_doctype": DOCTYPE, "reference_name": doc.name, "comment_type": "Comment"},
		fields=["owner", "creation", "content"],
		order_by="creation asc",
	)
	return {
		"name": doc.name,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"requested_by": doc.requested_by,
		"request_date": str(doc.request_date) if doc.request_date else None,
		"amount": doc.amount,
		"purpose": doc.purpose,
		"status": doc.status,
		"company": doc.company,
		"paid_from": doc.paid_from,
		"disbursed_by": doc.disbursed_by,
		"disbursed_on": str(doc.disbursed_on) if doc.disbursed_on else None,
		"journal_entry": doc.journal_entry,
		"can_disburse": _can_disburse(),
		"is_mine": doc.requested_by == frappe.session.user,
		"activity": [
			{"by": c.owner, "at": str(c.creation), "text": frappe.utils.strip_html(c.content or "").strip()}
			for c in comments
		],
	}


@frappe.whitelist()
def can_disburse():
	return {"can_disburse": _can_disburse()}


@frappe.whitelist()
def get_request(name: str):
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("read")
	return _serialize(doc)


@frappe.whitelist()
def save_request(payload):
	"""Create or edit a Requested petty cash request."""
	data = frappe.parse_json(payload)
	name = data.get("name")
	if name and frappe.db.exists(DOCTYPE, name):
		doc = frappe.get_doc(DOCTYPE, name)
		doc.check_permission("write")
		if doc.status != "Requested":
			frappe.throw(_("Only a Requested petty cash request can be edited."))
	else:
		doc = frappe.new_doc(DOCTYPE)

	doc.project = data.get("project")
	doc.amount = flt(data.get("amount"))
	doc.purpose = data.get("purpose")
	if data.get("request_date"):
		doc.request_date = data.get("request_date")
	if data.get("requested_by") and _can_disburse():
		doc.requested_by = data.get("requested_by")  # an approver may raise on behalf of a holder
	doc.flags.ignore_permissions = True
	doc.save()
	return _serialize(doc)


@frappe.whitelist()
def disburse(name, paid_from):
	doc = frappe.get_doc(DOCTYPE, name)
	if not _can_disburse():
		frappe.throw(_("You are not authorised to disburse petty cash."), frappe.PermissionError)
	doc.disburse(paid_from)
	return _serialize(doc)


@frappe.whitelist()
def undisburse(name: str):
	"""Reverse a disbursement (cancel the JE, revert to Requested)."""
	doc = frappe.get_doc(DOCTYPE, name)
	if not _can_disburse():
		frappe.throw(_("You are not authorised to reverse a disbursement."), frappe.PermissionError)
	doc.cancel_disbursement()
	return _serialize(doc)


@frappe.whitelist()
def cancel_request(name: str):
	"""Withdraw a Requested request (mark Cancelled)."""
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("write")
	if doc.status != "Requested":
		frappe.throw(_("Only a Requested request can be cancelled."))
	doc.status = "Cancelled"
	doc.flags.ignore_permissions = True
	doc.save()
	return _serialize(doc)


@frappe.whitelist()
def delete_request(name: str):
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("delete")
	if doc.status == "Disbursed":
		frappe.throw(_("Reverse the disbursement before deleting."))
	frappe.delete_doc(DOCTYPE, name)
	return {"ok": True}


@frappe.whitelist()
def list_cash_bank_accounts(company):
	"""Cash/Bank ledger accounts to disburse FROM (the funding source), for the given
	company — excluding the Petty Cash account itself, since crediting Petty Cash on a
	disbursement (Dr Petty Cash / Cr Petty Cash) would be a no-op."""
	from buildsuite_core.utils.petty_cash import get_petty_cash_account

	filters = {"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}
	petty = get_petty_cash_account(company)
	if petty:
		filters["name"] = ["!=", petty]
	return frappe.get_all(
		"Account",
		filters=filters,
		fields=["name", "account_type"],
		order_by="account_type, name",
	)


@frappe.whitelist()
def holder_balances(company=None):
	"""Reconciled per-holder petty-cash position from the GL: disbursed (float in),
	spent (verified expense out) and the net balance in hand. One view over both the
	Petty Cash Request (disburse) and Expense Entry (spend) legs."""
	from buildsuite_core.utils.petty_cash import reconciled_holder_balances

	return reconciled_holder_balances(company)
