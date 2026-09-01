# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Bank & Cash Accounts setting (S229) — the master of finance accounts that surface
across Project Finance (Overview card, disburse / receive / pay modals, Cash & Bank
statement). Backed by ERPNext `Account` (account_type Bank / Cash, company-scoped);
the designated Petty Cash account is surfaced as its own type.

Balances are DERIVED: current balance = the stored opening balance ± every recorded
movement (the account's GL balance). Only the opening balance is editable here.
Single-company for now — routes via default_company(). See the single-company seam."""

import frappe
from frappe import _
from frappe.utils import flt

from buildsuite_core.utils.petty_cash import get_petty_cash_account
from buildsuite_core.utils.project import default_company

# Roles allowed to manage the finance-account master (mirrors the admin-only setting tile).
_MANAGE_ROLES = {
	"System Manager",
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite Accountant",
}
# type -> (root_type, account_type, parent group hint) for creating a new ledger account.
_TYPE_MAP = {
	"Bank": ("Asset", "Bank", "Bank Accounts"),
	"Cash": ("Asset", "Cash", "Cash In Hand"),
	"Petty Cash": ("Asset", "Cash", "Cash In Hand"),
}


def _can_manage():
	return bool(_MANAGE_ROLES & set(frappe.get_roles()))


def _guard():
	if not _can_manage():
		frappe.throw(_("You don't have permission to manage finance accounts."), frappe.PermissionError)


def _ledger_balance(account, company):
	from erpnext.accounts.utils import get_balance_on

	return flt(get_balance_on(account=account, company=company))


def _serialize(acc, petty, company):
	"""Shape one Account row for the setting (opening + derived current balance)."""
	opening = flt(acc.bs_opening_balance)
	acc_type = "Petty Cash" if acc.name == petty else acc.account_type
	return {
		"id": acc.name,
		"name": acc.account_name,
		"type": acc_type,
		"account_no": acc.account_number or "",
		"opening_balance": opening,
		"current_balance": opening + _ledger_balance(acc.name, company),
	}


@frappe.whitelist()
def list_finance_accounts(company: str | None = None):
	company = company or default_company()
	if not company:
		return []
	petty = get_petty_cash_account(company)
	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_name", "account_type", "account_number", "bs_opening_balance"],
		order_by="account_type, account_name",
	)
	return [_serialize(a, petty, company) for a in accounts]


@frappe.whitelist()
def save_finance_account(name: str, type: str, account_no: str | None = None, opening_balance: int = 0, account: str | None = None):
	"""Create or edit a finance account. `account` is the Account id when editing."""
	_guard()
	company = default_company()
	if not company:
		frappe.throw(_("No default company is configured."))
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Account name is required."))
	if type not in _TYPE_MAP:
		frappe.throw(_("Invalid account type."))

	if account:
		doc = frappe.get_doc("Account", account)
		if doc.company != company:
			frappe.throw(_("That account belongs to another company."))
		doc.account_name = name
		doc.account_number = account_no or None
		doc.bs_opening_balance = flt(opening_balance)
		doc.flags.ignore_permissions = True
		doc.save()
		return _serialize(doc, get_petty_cash_account(company), company)

	# --- create ---
	if frappe.db.exists("Account", {"account_name": name, "company": company}):
		frappe.throw(_("An account named {0} already exists.").format(name))
	root_type, account_type, parent_hint = _TYPE_MAP[type]
	from buildsuite_core.utils.subcontract_billing import _ensure_account

	acc_name = _ensure_account(company, name, root_type, account_type, parent_hint)
	doc = frappe.get_doc("Account", acc_name)
	doc.account_number = account_no or None
	doc.bs_opening_balance = flt(opening_balance)
	doc.flags.ignore_permissions = True
	doc.save()
	return _serialize(doc, get_petty_cash_account(company), company)


@frappe.whitelist()
def delete_finance_account(account: str):
	"""Delete a finance account. Refused if it has any posted GL movement."""
	_guard()
	company = default_company()
	if frappe.db.get_value("Account", account, "company") != company:
		frappe.throw(_("That account belongs to another company."))
	if frappe.db.exists("GL Entry", {"account": account, "is_cancelled": 0}):
		frappe.throw(_("Accounts with recorded movements can't be deleted."))
	frappe.delete_doc("Account", account, ignore_permissions=True)
	return {"ok": True}
