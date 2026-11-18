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
def direct_expenses_hint(company) -> str:
	"""The parent for subcontractor charges: a subcontractor's work is a direct cost of the job, so
	it sits under "Direct Expenses". A chart of accounts without that group falls back to the
	root "Expenses"."""
	if frappe.db.exists("Account", {"account_name": "Direct Expenses", "company": company, "is_group": 1}):
		return "Direct Expenses"
	return "Expenses"


def resolve_accounts(company):
	"""Return {expense, retention, advance, cost_center} for a company, creating the BuildSuite
	accounts if a prior seed pass has not. Idempotent.

	Retention/advance are created with a BLANK account_type on purpose: ERPNext's "Payable"
	type forces a party subledger (a supplier) on every GL line, but retention is withheld
	against the company, not a party — so a plain Current Liability / Current Asset ledger."""
	return {
		"expense": _ensure_account(
			company, EXPENSE_ACCOUNT_NAME, "Expense", "Expense Account", direct_expenses_hint(company)
		),
		"retention": _ensure_account(company, RETENTION_ACCOUNT_NAME, "Liability", "", "Current Liabilities"),
		"advance": _ensure_account(company, ADVANCE_ACCOUNT_NAME, "Asset", "", "Current Assets"),
		"cost_center": frappe.db.get_value("Company", company, "cost_center"),
	}


def _ensure_account(company, account_name, root_type, account_type, parent_hint):
	"""Find (by name, per company) or create a postable ledger Account. Parent is the
	`parent_hint` group for this company, else any group of `root_type`.

	Always returns a ledger: Journal Entries and invoices reject group accounts, and some charts
	ship a group under the same name (e.g. the UAE chart's "Petty Cash"). When the name only
	exists as a group, a "<name> Ledger" account is created beneath it instead."""
	abbr = frappe.db.get_value("Company", company, "abbr")
	existing = frappe.db.get_value(
		"Account", {"account_name": account_name, "company": company}, ["name", "is_group"], as_dict=True
	)
	if existing and not existing.is_group:
		return existing.name
	if existing:  # a group of that name: use (or create) a ledger beneath it
		account_name = f"{account_name} Ledger"
		full_name = f"{account_name} - {abbr}"
		if frappe.db.exists("Account", full_name):
			return full_name
		parent = existing.name
	else:
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


SERVICE_UOM = "Subcontract Unit"


def _ensure_service_uom():
	"""A fraction-allowing UOM for the generic subcontract service item. ERPNext's default 'Nos'
	is whole-number only, which rejects the measured (often fractional) quantities a subcontractor
	bill carries, so those quantities failed to post to the Purchase Invoice."""
	if not frappe.db.exists("UOM", SERVICE_UOM):
		frappe.get_doc({"doctype": "UOM", "uom_name": SERVICE_UOM, "must_be_whole_number": 0}).insert(
			ignore_permissions=True
		)
	return SERVICE_UOM


def _list_stock_uom(item_code):
	"""ERPNext records an Item Price in the item's stock unit for every invoice line, and refuses
	one ("UOM ... not found in Item") when the item's own unit table doesn't list that unit. Add
	the stock unit to the table if it's missing, without otherwise touching the item."""
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if stock_uom == SERVICE_UOM:
		_ensure_service_uom()
	if frappe.db.exists(
		"UOM Conversion Detail", {"parenttype": "Item", "parent": item_code, "uom": stock_uom}
	):
		return stock_uom
	item = frappe.get_doc("Item", item_code)
	item.append("uoms", {"uom": stock_uom, "conversion_factor": 1}).db_insert()
	return stock_uom


def ensure_service_item(fractional_uom=True):
	"""The single non-stock service Item all bill lines map to on the PI. Its description
	carries the real work; users never pick it on the Vue screen.

	`fractional_uom=False` (a direct bill, whose lines are whole lump sums) leaves an existing
	item on whatever unit it has, so a direct bill never depends on the fractional unit."""
	if frappe.db.exists("Item", SERVICE_ITEM) and not fractional_uom:
		_list_stock_uom(SERVICE_ITEM)
		return SERVICE_ITEM
	uom = _ensure_service_uom()
	if frappe.db.exists("Item", SERVICE_ITEM):
		# Older installs created this on ERPNext's default 'Nos' (whole-number only), so fractional
		# measured quantities were rejected. Move it onto the fraction-allowing UOM — it's a
		# non-stock item, so there's no stock ledger to block the change. The UOM must also be in
		# the item's conversion table, or ERPNext refuses the PI line ("UOM ... not found in Item").
		item = frappe.get_doc("Item", SERVICE_ITEM)
		if item.stock_uom != uom or not any(u.uom == uom for u in item.uoms):
			item.stock_uom = uom
			if not any(u.uom == uom for u in item.uoms):
				item.append("uoms", {"uom": uom, "conversion_factor": 1})
			item.flags.ignore_permissions = True
			item.save()
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
			"stock_uom": uom,
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
	item_code = ensure_service_item(fractional_uom=not bill.is_direct)
	item_uom = frappe.db.get_value("Item", item_code, "stock_uom")
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
	# The supplier's own invoice reference (optional) carries to the PI's bill no/date; fall
	# back to our bill name/date when the subcontractor didn't give a separate invoice number.
	pi.bill_no = bill.get("supplier_invoice_no") or bill.name
	pi.bill_date = str(bill.supplier_invoice_date) if bill.get("supplier_invoice_date") else bill_date
	pi.project = bill.project
	pi.update_stock = 0
	if frappe.get_meta("Purchase Invoice").has_field("subcontractor_bill"):
		pi.subcontractor_bill = bill.name

	for line in bill.lines:
		amount = flt(line.this_period_amount)
		if amount <= 0:
			continue
		if bill.is_direct:
			# A direct line is a typed lump sum: one unit of the item's own stock unit at the amount.
			qty, rate, uom = 1, amount, item_uom
		else:
			qty = flt(line.this_period_qty) or 1
			rate = flt(line.rate) or (amount / qty if qty else amount)
			uom = line.uom or None
		pi.append(
			"items",
			{
				"item_code": item_code,
				"description": line.scope or line.cost_code_label or SERVICE_ITEM,
				"qty": qty,
				"rate": rate,
				"amount": amount,
				"uom": uom,
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

	# The approval happened on the Subcontractor Bill; the PI is an internal accounting artifact
	# submitted here directly. If a site has enabled the (opt-in) Purchase Invoice workflow, stamp
	# the PI to that workflow's submitted state so it doesn't sit in the approval queue and its
	# workflow_state stays consistent with docstatus.
	from buildsuite_core.api.workflow import submitted_state

	pi_submitted_state = submitted_state("Purchase Invoice")
	if pi_submitted_state:
		pi.workflow_state = pi_submitted_state

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
