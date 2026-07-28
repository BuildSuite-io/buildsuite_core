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


def _cost_code_fields(cost_code):
	"""Flatten the picker's cost-code object → the four stored line fields (same shape as
	subcontractor lines). Accepts the {type, group_code, item_code, label} object or None."""
	if not cost_code or not isinstance(cost_code, dict):
		return {"cost_code_type": "", "cost_code_group": "", "cost_code_item": "", "cost_code_label": ""}
	return {
		"cost_code_type": "Item" if cost_code.get("type") == "item" else "Group",
		"cost_code_group": cost_code.get("group_code") or "",
		"cost_code_item": cost_code.get("item_code") or "",
		"cost_code_label": cost_code.get("label") or "",
	}


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
def list_expenses():
	"""Flattened expense records (one per Expense Entry) shaped like the prototype's
	list: date, description, holder, source, account, cost type, amount, status."""
	entries = frappe.get_all(
		DOCTYPE,
		fields=["name", "date", "project", "company", "employee", "employee_name", "total_amount", "docstatus", "paid_from", "payment_account", "description"],
		order_by="date desc, creation desc",
		limit_page_length=0,
	)
	if not entries:
		return []

	names = [e.name for e in entries]
	first = {}
	for r in frappe.get_all(
		"Expense Entry Table",
		filters={"parent": ["in", names]},
		fields=["parent", "expense_account", "cost_code_label", "attachment", "description"],
		order_by="idx asc",
	):
		first.setdefault(r.parent, r)

	proj = {}
	pids = list({e.project for e in entries if e.project})
	if pids:
		proj = {p.name: p.project_name for p in frappe.get_all("Project", filters={"name": ["in", pids]}, fields=["name", "project_name"])}

	status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
	out = []
	for e in entries:
		fr = first.get(e.name) or {}
		out.append(
			{
				"name": e.name,
				"date": str(e.date) if e.date else None,
				"description": fr.get("description") or e.description or e.name,
				"project": e.project,
				"project_name": proj.get(e.project) or e.project,
				"company": e.company,
				"employee": e.employee,
				"employee_name": e.employee_name or e.employee,
				"source": e.paid_from or "Petty Cash",
				"payment_account": e.payment_account,
				"expense_account": fr.get("expense_account"),
				"cost_code": fr.get("cost_code_label"),
				"attachment": fr.get("attachment"),
				"amount": e.total_amount,
				"status": status_map.get(e.docstatus, "Draft"),
			}
		)
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
		"paid_from": doc.paid_from,
		"journal_entry": doc.journal_entry,
		"description": doc.description,
		"rows": [
			{
				"expense_account": r.expense_account,
				# Reconstruct the cost-code object the picker binds to (see subcontract lines).
				"cost_code": (
					{
						"type": (r.cost_code_type or "").lower(),
						"group_code": r.cost_code_group or "",
						"item_code": r.cost_code_item or None,
						"label": r.cost_code_label or "",
					}
					if r.cost_code_label
					else None
				),
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
	"""Create or edit a draft Expense Entry (PF-04).

	rows: [{expense_account, amount, description, project?}]. `paid_from` is either
	"petty" (Cr the company Petty Cash account, holder mandatory) or "company" (Cr a
	Bank/Cash account chosen via `company_account`, no holder).

	Holder rules: an ordinary user can only spend their own float, so the holder is
	forced to their linked Employee. An approver/accountant may raise against any
	holder by passing `employee`.
	"""
	data = frappe.parse_json(payload)

	project = data.get("project")
	if not project:
		frappe.throw(_("A project is required."))
	company = frappe.db.get_value("Project", project, "company")

	paid_from = "Company" if data.get("paid_from") == "company" else "Petty Cash"

	if paid_from == "Company":
		employee = None
		account = data.get("company_account")
		if not account:
			frappe.throw(_("Choose the company Bank/Cash account to pay from."))
		if frappe.db.get_value("Account", account, "company") != company:
			frappe.throw(_("The selected account does not belong to {0}.").format(company))
	else:
		# Approvers may record on behalf of any holder; everyone else is pinned to their own.
		employee = data.get("employee") if _can_submit() else None
		employee = employee or _current_employee()
		if not employee:
			frappe.throw(_("No active Employee is linked to your user account."))
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
	doc.paid_from = paid_from
	for r in rows:
		doc.append(
			"expense_entry_table",
			{
				"employee": employee,
				"payment_account": account,
				"expense_account": r.get("expense_account"),
				**_cost_code_fields(r.get("cost_code")),
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
def list_cash_bank_accounts(project=None, company=None):
	"""Bank/Cash accounts a Company-paid expense can be drawn from (excludes Petty Cash).

	Accepts a project (company is derived from it, matching save_expense) or a company.
	"""
	if project and not company:
		company = frappe.db.get_value("Project", project, "company")
	if not company:
		return []
	petty = pc.get_petty_cash_account(company)
	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_type"],
		order_by="account_type, name",
	)
	return [a for a in accounts if a.name != petty]


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
