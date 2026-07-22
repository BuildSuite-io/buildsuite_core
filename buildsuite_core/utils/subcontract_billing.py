# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Subcontractor Bill → Purchase Invoice generation.

The Subcontractor Bill is the front-end instrument (free-text lines, retention, TDS,
discount, attachment). The Purchase Invoice it generates on submit does the accounting —
payable, taxes, TDS, retention — via ERPNext's own framework, so whatever country-compliance
app is installed (e.g. India Compliance, which hooks Purchase Invoice server-side) posts GST
automatically. Nothing here is GST-specific: taxes come from the bill's chosen tax template.
"""

import frappe
from frappe import _
from frappe.utils import flt

SERVICE_ITEM = "Subcontractor Work"
SERVICE_ITEM_GROUP = "Subcontract"
RETENTION_ACCOUNT_NAME = "Retention Payable"
EXPENSE_ACCOUNT_NAME = "Subcontractor Charges"
ADVANCE_ACCOUNT_NAME = "Supplier Advance"


# --------------------------------------------------------------------------- #
# Supplier resolution
# --------------------------------------------------------------------------- #
def ensure_supplier(subcontractor):
	"""A subcontractor IS a Supplier (supplier_type = "Subcontractor"), so the bill's
	`subcontractor` field already holds a Supplier name — just validate + return it."""
	if not subcontractor or not frappe.db.exists("Supplier", subcontractor):
		frappe.throw(_("Subcontractor {0} is not a valid Supplier.").format(subcontractor or "—"))
	return subcontractor


# --------------------------------------------------------------------------- #
# Account + service-item resolution (per company)
# --------------------------------------------------------------------------- #
def resolve_accounts(company):
	"""Return {expense, retention, advance, cost_center} for a company, creating the BuildSuite
	accounts if a prior seed pass has not. Idempotent.

	Retention/advance are created with a BLANK account_type on purpose: ERPNext's "Payable"
	type forces a party subledger (a supplier) on every GL line, but retention is withheld
	against the company, not a party — so a plain Current Liability / Current Asset ledger."""
	return {
		"expense": _ensure_account(company, EXPENSE_ACCOUNT_NAME, "Expense", "Expense Account", "Expenses"),
		"retention": _ensure_account(company, RETENTION_ACCOUNT_NAME, "Liability", "", "Current Liabilities"),
		"advance": _ensure_account(company, ADVANCE_ACCOUNT_NAME, "Asset", "", "Current Assets"),
		"cost_center": frappe.db.get_value("Company", company, "cost_center"),
	}


def _ensure_account(company, account_name, root_type, account_type, parent_hint):
	"""Find (by name, per company) or create a ledger Account. Parent is the `parent_hint`
	group for this company, else any group of `root_type`."""
	abbr = frappe.db.get_value("Company", company, "abbr")
	full_name = f"{account_name} - {abbr}"
	if frappe.db.exists("Account", full_name):
		return full_name
	existing = frappe.db.get_value(
		"Account", {"account_name": account_name, "company": company}, "name"
	)
	if existing:
		return existing

	parent = frappe.db.get_value(
		"Account", {"account_name": parent_hint, "company": company, "is_group": 1}, "name"
	)
	if not parent:
		parent = frappe.db.get_value(
			"Account", {"company": company, "is_group": 1, "root_type": root_type}, "name"
		)
	if not parent:
		frappe.throw(_("Could not resolve a parent account for {0} in {1}.").format(account_name, company))

	acc = frappe.new_doc("Account")
	acc.account_name = account_name
	acc.company = company
	acc.parent_account = parent
	acc.root_type = root_type
	if account_type:
		acc.account_type = account_type
	acc.flags.ignore_permissions = True
	acc.insert()
	return acc.name


def ensure_service_item():
	"""The single non-stock service Item all bill lines map to on the PI. Its description
	carries the real work; users never pick it on the Vue screen."""
	if frappe.db.exists("Item", SERVICE_ITEM):
		return SERVICE_ITEM
	if not frappe.db.exists("Item Group", SERVICE_ITEM_GROUP):
		parent = frappe.db.get_value("Item Group", {"is_group": 1}, "name") or "All Item Groups"
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": SERVICE_ITEM_GROUP, "parent_item_group": parent}
		).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": SERVICE_ITEM,
			"item_name": SERVICE_ITEM,
			"item_group": SERVICE_ITEM_GROUP,
			"is_stock_item": 0,
			"is_purchase_item": 1,
			"is_sales_item": 0,
			"description": "Subcontracted work — the bill line description carries the real scope.",
		}
	).insert(ignore_permissions=True)
	return SERVICE_ITEM


def resolve_expense_account(bill, fallback):
	"""The expense account the PI posts the subcontract cost to: the bill's own override,
	else the BuildSuite Core Settings default, else the per-company 'Subcontractor Charges'.
	The settings default is only honoured when it belongs to the bill's company."""
	if bill.get("expense_account"):
		return bill.expense_account
	default = frappe.db.get_single_value("BuildSuite Core Settings", "default_subcontractor_expense_account")
	if default and frappe.db.get_value("Account", default, "company") == bill.company:
		return default
	return fallback


def settings_expense_account_for(company):
	"""The default expense account to pre-fill on a new bill, if it matches the company."""
	default = frappe.db.get_single_value("BuildSuite Core Settings", "default_subcontractor_expense_account")
	if default and frappe.db.get_value("Account", default, "company") == company:
		return default
	return None


# --------------------------------------------------------------------------- #
# Purchase Invoice generation
# --------------------------------------------------------------------------- #
def retention_held_before(bill):
	"""Total retention withheld by this WO/subcontractor's earlier SUBMITTED bills — released
	on a Final bill."""
	filters = {"docstatus": 1, "name": ["!=", bill.name or ""]}
	if bill.work_order:
		filters["work_order"] = bill.work_order
	else:
		filters["subcontractor"] = bill.subcontractor
		filters["is_direct"] = 1
	rows = frappe.get_all("Subcontractor Bill", filters=filters, fields=["retention_amount"])
	return sum(flt(r.retention_amount) for r in rows)


def generate_purchase_invoice(bill):
	"""Build, insert and submit the Purchase Invoice for a submitted Subcontractor Bill.

	Idempotent (returns the existing PI if already linked). Raises on any failure so the
	enclosing bill submit rolls back — never leaving a submitted bill without a PI."""
	if bill.purchase_invoice and frappe.db.exists("Purchase Invoice", bill.purchase_invoice):
		return bill.purchase_invoice

	supplier = ensure_supplier(bill.subcontractor)
	item_code = ensure_service_item()
	accts = resolve_accounts(bill.company)
	expense_account = resolve_expense_account(bill, accts["expense"])

	pi = frappe.new_doc("Purchase Invoice")
	pi.company = bill.company
	pi.supplier = supplier
	pi.currency = frappe.db.get_value("Company", bill.company, "default_currency")
	# ERPNext's get_due_date() is strictly typed (str | None) — a DB-loaded Date field is a
	# datetime.date, which pydantic rejects. Pass ISO strings.
	bill_date = str(bill.date) if bill.date else None
	pi.set_posting_time = 1
	pi.posting_date = bill_date
	pi.bill_no = bill.name
	pi.bill_date = bill_date
	pi.project = bill.project
	pi.update_stock = 0
	if frappe.get_meta("Purchase Invoice").has_field("subcontractor_bill"):
		pi.subcontractor_bill = bill.name

	for line in bill.lines:
		amount = flt(line.this_period_amount)
		if amount <= 0:
			continue
		qty = flt(line.this_period_qty) or 1
		rate = flt(line.rate) or (amount / qty if qty else amount)
		pi.append(
			"items",
			{
				"item_code": item_code,
				"description": line.scope or line.cost_code_label or SERVICE_ITEM,
				"qty": qty,
				"rate": rate,
				"amount": amount,
				"uom": line.uom or None,
				"expense_account": expense_account,
				"cost_center": accts["cost_center"],
				"project": bill.project,
			},
		)

	if not pi.items:
		frappe.throw(_("Nothing to invoice — every line is zero."))

	# Taxes: the bill's chosen template rows (Add), then retention / advance (Deduct), and a
	# Final-bill retention release (Add).
	for t in bill.taxes:
		pi.append(
			"taxes",
			{
				"charge_type": t.charge_type or "On Net Total",
				"account_head": t.account_head,
				"description": t.description or t.account_head,
				"rate": flt(t.rate),
				"category": "Total",
				"add_deduct_tax": "Add",
			},
		)
	if flt(bill.retention_amount) > 0 and bill.bill_type != "Final":
		_append_actual(pi, accts["retention"], _("Retention"), flt(bill.retention_amount), "Deduct")
	if bill.bill_type == "Final":
		release = retention_held_before(bill)
		if release > 0:
			_append_actual(pi, accts["retention"], _("Retention Release"), release, "Add")
	if flt(bill.advance_recovery) > 0:
		_append_actual(pi, accts["advance"], _("Advance Recovery"), flt(bill.advance_recovery), "Deduct")

	# Discount → native PI fields.
	if bill.additional_discount_on:
		pi.apply_discount_on = bill.additional_discount_on
	if flt(bill.discount_amount) > 0:
		pi.discount_amount = flt(bill.discount_amount)
	elif flt(bill.additional_discount_percentage) > 0:
		pi.additional_discount_percentage = flt(bill.additional_discount_percentage)

	# TDS → ERPNext computes withholding from the category on submit.
	if bill.apply_tds and bill.tax_withholding_category:
		pi.apply_tds = 1
		pi.tax_withholding_category = bill.tax_withholding_category

	pi.flags.ignore_permissions = True
	pi.set_missing_values()
	pi.insert()
	pi.submit()
	return pi.name


def _append_actual(pi, account_head, description, amount, add_deduct):
	pi.append(
		"taxes",
		{
			"charge_type": "Actual",
			"account_head": account_head,
			"description": description,
			"rate": 0,
			"tax_amount": amount,
			"category": "Total",
			"add_deduct_tax": add_deduct,
		},
	)
