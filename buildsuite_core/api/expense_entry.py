# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Project Finance › Expenses (petty cash) panel.

The signed-in user spends against their petty-cash float by raising an Expense Entry
(draft = pending approval); a finance approver submits it, which posts the Journal
Entry and settles the balance. These endpoints resolve the caller's Employee and
surface their live balance + ledger from utils.petty_cash.
"""

import frappe
from frappe import _
from frappe.utils import flt

from buildsuite_core.utils import petty_cash as pc

DOCTYPE = "Expense Entry"


def _current_employee(user=None):
	"""The active Employee linked to the (given or session) user, or None."""
	return pc.employee_for_user(user or frappe.session.user)


def _can_submit():
	from buildsuite_core.permissions.setup import PETTY_CASH_DISBURSE_ROLES

	return bool(set(frappe.get_roles()) & set(PETTY_CASH_DISBURSE_ROLES))


@frappe.whitelist()
def context():
	"""The caller's petty-cash position: linked employee + balances, for the panel header."""
	employee = _current_employee()
	out = {
		"employee": employee,
		"employee_name": frappe.db.get_value("Employee", employee, "employee_name") if employee else None,
		"can_submit": _can_submit(),
		"approved": 0,
		"pending": 0,
		"available": 0,
	}
	if not employee:
		return out
	out["approved"] = flt(pc.get_balance_amount_approved(employee))
	out["pending"] = flt(pc.get_pending_approval_balance(employee))
	out["available"] = flt(pc.get_total_balance_include_review(employee))
	return out


@frappe.whitelist()
def get_expense(name):
	"""Full expense entry (parent + lines) for the detail modal."""
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"date": str(doc.date) if doc.date else None,
		"company": doc.company,
		"project": doc.project,
		"employee": doc.employee,
		"employee_name": frappe.db.get_value("Employee", doc.employee, "employee_name") if doc.employee else None,
		"payment_account": doc.payment_account,
		"total_amount": doc.total_amount,
		"docstatus": doc.docstatus,
		"reimbursable": doc.reimbursable,
		"reimbursed": doc.reimbursed,
		"reimbursed_on": str(doc.reimbursed_on) if doc.reimbursed_on else None,
		"journal_entry": doc.journal_entry,
		"reimbursement_journal_entry": doc.reimbursement_journal_entry,
		"description": doc.description,
		"rows": [
			{
				"expense_account": r.expense_account,
				"cost_type": r.cost_type,
				"description": r.description,
				"amount": r.amount,
				"attachment": r.attachment,
				"project": r.project,
			}
			for r in doc.expense_entry_table
		],
	}


@frappe.whitelist()
def ledger(transaction_type=None, project=None, from_date=None, to_date=None):
	"""Petty-cash transaction ledger for the caller's employee (newest first)."""
	employee = _current_employee()
	if not employee:
		return []
	return pc.get_transaction_list(employee, transaction_type, project, from_date, to_date)


@frappe.whitelist()
def save_expense(payload):
	"""Create or edit a draft Expense Entry paid from the caller's petty cash.

	rows: [{expense_account, amount, description, project?}]. Employee + payment
	account are resolved server-side so a holder can only spend their own float.
	"""
	data = frappe.parse_json(payload)
	employee = _current_employee()
	if not employee:
		frappe.throw(_("No active Employee is linked to your user account."))

	project = data.get("project")
	if not project:
		frappe.throw(_("A project is required."))
	company = frappe.db.get_value("Project", project, "company")

	# Out-of-pocket spend parks in Employee Reimbursements (a payable) so it doesn't
	# touch the petty-cash float; otherwise it's paid straight from Petty Cash.
	reimbursable = 1 if data.get("reimbursable") else 0
	if reimbursable:
		account = pc.resolve_reimbursements_account(company)
	else:
		account = pc.get_petty_cash_account(company)
		if not account:
			frappe.throw(_("Petty Cash account not found for {0}.").format(company))

	rows = data.get("rows") or []
	if not rows:
		frappe.throw(_("Add at least one expense line."))

	name = data.get("name")
	if name and frappe.db.exists(DOCTYPE, name):
		doc = frappe.get_doc(DOCTYPE, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft expense entry can be edited."))
		doc.set("expense_entry_table", [])
	else:
		doc = frappe.new_doc(DOCTYPE)

	doc.date = data.get("date") or frappe.utils.today()
	doc.company = company
	doc.project = project
	doc.employee = employee
	doc.payment_account = account
	doc.reimbursable = reimbursable
	for r in rows:
		doc.append(
			"expense_entry_table",
			{
				"employee": employee,
				"payment_account": account,
				"expense_account": r.get("expense_account"),
				"cost_type": r.get("cost_type") or "Overhead",
				"project": r.get("project") or project,
				"amount": flt(r.get("amount")),
				"description": r.get("description"),
				"attachment": r.get("attachment"),
			},
		)
	doc.flags.ignore_permissions = True
	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def to_reimburse():
	"""Submitted out-of-pocket expenses awaiting reimbursement (approver queue)."""
	rows = frappe.get_all(
		DOCTYPE,
		filters={"docstatus": 1, "reimbursable": 1, "reimbursed": 0},
		fields=["name", "date", "project", "employee", "employee_name", "company", "total_amount"],
		order_by="date asc",
	)
	return {"rows": rows, "total": sum(flt(r.total_amount) for r in rows)}


@frappe.whitelist()
def reimburse(name, bank_account):
	"""Pay an employee back for an out-of-pocket expense (posts the reimbursement JE)."""
	if not _can_submit():
		frappe.throw(_("You are not authorised to reimburse expenses."), frappe.PermissionError)
	doc = frappe.get_doc(DOCTYPE, name)
	je = doc.reimburse(bank_account)
	return {"name": doc.name, "reimbursement_journal_entry": je}


@frappe.whitelist()
def list_cash_bank_accounts(company):
	"""Bank/Cash accounts to pay a reimbursement from."""
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_type"],
		order_by="account_type, name",
	)


@frappe.whitelist()
def submit_expense(name):
	"""Approve (submit) a draft Expense Entry — posts the Journal Entry."""
	if not _can_submit():
		frappe.throw(_("You are not authorised to approve expense entries."), frappe.PermissionError)
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.docstatus != 0:
		frappe.throw(_("Only a draft expense entry can be approved."))
	doc.flags.ignore_permissions = True
	doc.submit()
	return {"name": doc.name, "journal_entry": doc.journal_entry}


@frappe.whitelist()
def cancel_expense(name):
	"""Cancel a submitted Expense Entry (reverses its Journal Entry) or delete a draft."""
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.docstatus == 1:
		if not _can_submit():
			frappe.throw(_("You are not authorised to cancel expense entries."), frappe.PermissionError)
		doc.flags.ignore_permissions = True
		doc.cancel()
		return {"name": name, "cancelled": True}
	doc.check_permission("delete")
	frappe.delete_doc(DOCTYPE, name)
	return {"name": name, "deleted": True}


@frappe.whitelist()
def list_expense_accounts(company):
	"""Expense (P&L) ledger accounts for the row picker."""
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "root_type": "Expense"},
		fields=["name"],
		order_by="name",
		limit_page_length=0,
	)
