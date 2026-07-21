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
# Supplier resolution (auto-create from Subcontractor)
# --------------------------------------------------------------------------- #
def ensure_supplier(subcontractor):
	"""Return the ERPNext Supplier linked to a Subcontractor, creating one if absent.

	A Purchase Invoice needs a Supplier; a Subcontractor's `supplier` link is optional, so on
	first bill submit we create the Supplier from the Subcontractor's details and link it back.
	The subcontractor's tax ids are carried across when the Supplier custom fields exist
	(India Compliance adds gstin/pan; core ERPNext has tax_id)."""
	sub = frappe.get_doc("Subcontractor", subcontractor)
	if sub.supplier and frappe.db.exists("Supplier", sub.supplier):
		return sub.supplier

	supplier = frappe.new_doc("Supplier")
	supplier.supplier_name = sub.subcontractor_name
	supplier.supplier_group = _default_supplier_group()
	supplier.supplier_type = "Company"
	# Carry tax ids across when the target fields exist on Supplier. The Subcontractor's
	# fields are country-neutral (tax_id / secondary_tax_id); India Compliance's Supplier
	# custom fields (gstin/pan) receive them when present.
	primary = _tax_id_of(sub)
	secondary = getattr(sub, "secondary_tax_id", None)
	meta = frappe.get_meta("Supplier")
	if primary and meta.has_field("tax_id"):
		supplier.tax_id = primary
	if primary and meta.has_field("gstin"):
		supplier.gstin = primary
	if secondary and meta.has_field("pan"):
		supplier.pan = secondary
	supplier.flags.ignore_permissions = True
	supplier.insert()

	sub.db_set("supplier", supplier.name)
	return supplier.name


def _tax_id_of(sub):
	"""Primary tax id off a Subcontractor, tolerant of the field name (country-neutral
	tax_id, or legacy gstin on an un-migrated site)."""
	for f in ("tax_id", "gstin"):
		if hasattr(sub, f) and getattr(sub, f):
			return getattr(sub, f)
	return None


def _default_supplier_group():
	for name in ("Subcontractor", "Services", "All Supplier Groups"):
		if frappe.db.exists("Supplier Group", name):
			return name
	# Fall back to any leaf group.
	grp = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	return grp or "All Supplier Groups"


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

	pi = frappe.new_doc("Purchase Invoice")
	pi.company = bill.company
	pi.supplier = supplier
	pi.currency = frappe.db.get_value("Company", bill.company, "default_currency")
	pi.set_posting_time = 1
	pi.posting_date = bill.date
	pi.bill_no = bill.name
	pi.bill_date = bill.date
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
				"expense_account": accts["expense"],
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
