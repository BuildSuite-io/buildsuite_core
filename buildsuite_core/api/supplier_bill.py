# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Bills — the direct SUPPLIER bill, a thin front-end over ERPNext's
Purchase Invoice (money out). Mirrors the customer-invoice (Sales Invoice) wrapper: create a
draft, submit (posts the payable), and pay (a real Payment Entry from a Bank/Cash account).
Subcontractor bills are a separate doctype and reuse their own screens; the Bills panel lists
both via list_payables. Single-company for now (see the single-company seam)."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from buildsuite_core.utils.project import default_company

PI = "Purchase Invoice"
PE = "Payment Entry"
SERVICE_ITEM = "Supplier Charges"
SERVICE_ITEM_GROUP = "Services"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _company_for(project=None):
	if project:
		return frappe.db.get_value("Project", project, "company") or default_company()
	return default_company()


def ensure_bill_item():
	"""A generic non-stock purchase Item that bill lines hang off (the description carries the
	real detail)."""
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
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 0,
			"is_purchase_item": 1,
		}
	).insert(ignore_permissions=True)
	return SERVICE_ITEM


def _expense_account(company):
	acc = frappe.db.get_value("Company", company, "default_expense_account")
	if acc:
		return acc
	from buildsuite_core.utils.subcontract_billing import _ensure_account

	return _ensure_account(company, "Cost of Goods Sold", "Expense", "Expense Account", "Expenses")


def _payment_summary(name):
	pi = frappe.db.get_value(
		PI, name, ["grand_total", "outstanding_amount", "status", "docstatus"], as_dict=True
	)
	if not pi or pi.docstatus == 0:
		return {"invoiced": 0, "paid": 0, "outstanding": 0, "status": "Draft"}
	invoiced = flt(pi.grand_total)
	outstanding = flt(pi.outstanding_amount)
	paid = invoiced - outstanding
	if pi.docstatus == 2:
		status = "Cancelled"
	elif outstanding <= 0.01 and invoiced > 0:
		status = "Paid"
	elif paid > 0.01:
		status = "Partly Paid"
	else:
		status = "Unpaid"
	return {"invoiced": invoiced, "paid": paid, "outstanding": outstanding, "status": status}


def _ref_is_advance(pe_type, paid_amount, unallocated, allocated):
	"""True when a Payment Entry linked to a bill is a supplier ADVANCE (on-account money adjusted
	against the bill) rather than a plain payment raised for that one bill. A payment (via
	record_payment) is a Pay fully consumed 1:1 by the bill; an advance still carries unallocated
	money or funds more than this allocation."""
	if pe_type != "Pay":
		return False
	return flt(unallocated) > 0.01 or flt(paid_amount) - flt(allocated) > 0.01


def _linked_advances(doc):
	"""Advances adjusted against this bill, one entry per Payment Entry with its TOTAL applied.

	Draft → the native `advances` table. Submitted → the advance Payment Entry's references to
	this bill, SUMMED per Payment Entry (a partial advance may be reconciled in several steps).
	A Payment Entry counts as an advance when it was set on the bill before submit (its
	advances-table row is retained after submit) or when it is an on-account payment reconciled
	after submit — a plain cash payment is neither."""
	if doc.docstatus == 0:
		return [
			{"payment_entry": a.reference_name, "allocated": flt(a.allocated_amount)}
			for a in doc.advances
			if a.reference_type == PE and flt(a.allocated_amount) > 0
		]

	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": PI, "reference_name": doc.name, "docstatus": 1},
		fields=["parent", "allocated_amount"],
		order_by="creation asc",
	)
	totals, order = {}, []
	for r in refs:
		if r.parent not in totals:
			totals[r.parent] = 0
			order.append(r.parent)
		totals[r.parent] += flt(r.allocated_amount)

	table_pes = {
		a.reference_name for a in doc.advances if a.reference_type == PE and flt(a.allocated_amount) > 0
	}
	out = []
	for pe_name in order:
		total = totals[pe_name]
		is_advance = pe_name in table_pes
		if not is_advance:
			pe = frappe.db.get_value(
				PE, pe_name, ["payment_type", "paid_amount", "unallocated_amount"], as_dict=True
			)
			is_advance = bool(pe) and _ref_is_advance(
				pe.payment_type, pe.paid_amount, pe.unallocated_amount, total
			)
		if is_advance:
			out.append({"payment_entry": pe_name, "allocated": total})
	return out


def _serialize(doc):
	advances = _linked_advances(doc)
	adjusted = sum(a["allocated"] for a in advances)
	pay = _payment_summary(doc.name)
	# Advance adjustment settles the payable but is not a cash payment — split it out of "Paid"
	# so the totals read the way the prototype shows them.
	pay["advance_adjusted"] = adjusted
	if doc.docstatus == 1:
		pay["paid"] = max(flt(pay["paid"]) - adjusted, 0)
	return {
		"name": doc.name,
		"kind": "supplier",
		"supplier": doc.supplier,
		"supplier_name": doc.supplier_name,
		"supplier_gstin": frappe.db.get_value("Supplier", doc.supplier, "tax_id") if doc.supplier else None,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"company": doc.company,
		"date": str(doc.posting_date) if doc.posting_date else None,
		"due_date": str(doc.due_date) if doc.due_date else None,
		"bill_no": doc.bill_no,
		"bill_date": str(doc.bill_date) if doc.bill_date else None,
		"taxes_and_charges": doc.taxes_and_charges,
		"additional_discount_on": doc.apply_discount_on or "Net Total",
		"additional_discount_percentage": doc.additional_discount_percentage,
		"discount_amount": doc.discount_amount,
		"terms": doc.terms,
		"tc_name": doc.tc_name,
		"docstatus": doc.docstatus,
		"net_total": doc.net_total,
		"total_taxes_and_charges": doc.total_taxes_and_charges,
		"grand_total": doc.grand_total,
		"advance_adjusted": adjusted,
		"advances": advances,
		"items": [
			{
				"item_code": r.item_code,
				"description": r.description,
				"qty": r.qty,
				"uom": r.uom,
				"rate": r.rate,
				"amount": r.amount,
				"purchase_order": r.get("purchase_order"),
				"po_detail": r.get("po_detail"),
			}
			for r in doc.items
		],
		"taxes": [
			{
				"charge_type": t.charge_type,
				"account_head": t.account_head,
				"description": t.description,
				"rate": t.rate,
				"tax_amount": t.tax_amount,
			}
			for t in doc.taxes
		],
		"payment": pay,
	}


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_bill(name):
	doc = frappe.get_doc(PI, name)
	doc.check_permission("read")
	return _serialize(doc)


@frappe.whitelist()
def list_payables(company=None):
	"""Unified Bills list: direct supplier Purchase Invoices + submitted Subcontractor Bills.
	A subcontractor bill's own generated PI (which carries `subcontractor_bill`) is excluded so
	it isn't counted twice."""
	company = company or default_company()
	rows = []

	# Direct supplier bills — Purchase Invoices NOT generated by a subcontractor bill.
	has_link = frappe.get_meta(PI).has_field("subcontractor_bill")
	pi_filters = {"company": company, "docstatus": ["<", 2]}
	if has_link:
		pi_filters["subcontractor_bill"] = ["in", ["", None]]
	for pi in frappe.get_all(
		PI,
		filters=pi_filters,
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"project",
			"posting_date",
			"due_date",
			"grand_total",
			"outstanding_amount",
			"status",
			"docstatus",
		],
		order_by="posting_date desc, creation desc",
	):
		rows.append(
			{
				"kind": "supplier",
				"name": pi.name,
				"party": pi.supplier_name or pi.supplier,
				"project": pi.project,
				"date": str(pi.posting_date) if pi.posting_date else None,
				"due_date": str(pi.due_date) if pi.due_date else None,
				"total": flt(pi.grand_total),
				"outstanding": flt(pi.outstanding_amount) if pi.docstatus == 1 else 0,
				"docstatus": pi.docstatus,
				"status": _pay_status(pi.docstatus, flt(pi.grand_total), flt(pi.outstanding_amount)),
			}
		)

	# Submitted subcontractor bills — outstanding read through their generated PI.
	for sb in frappe.get_all(
		"Subcontractor Bill",
		filters={"company": company, "docstatus": 1},
		fields=["name", "subcontractor_name", "project", "date", "net_payable", "purchase_invoice", "ra_no"],
		order_by="date desc, creation desc",
	):
		grand = flt(sb.net_payable)
		outstanding = grand
		if sb.purchase_invoice and frappe.db.exists(PI, sb.purchase_invoice):
			pi = frappe.db.get_value(
				PI, sb.purchase_invoice, ["grand_total", "outstanding_amount"], as_dict=True
			)
			grand = flt(pi.grand_total)
			outstanding = flt(pi.outstanding_amount)
		rows.append(
			{
				"kind": "subcontractor",
				"name": sb.name,
				"party": sb.subcontractor_name,
				"project": sb.project,
				"date": str(sb.date) if sb.date else None,
				"due_date": None,
				"total": grand,
				"outstanding": outstanding,
				"docstatus": 1,
				"status": _pay_status(1, grand, outstanding),
			}
		)

	rows.sort(key=lambda r: (r["date"] or ""), reverse=True)
	return rows


def _pay_status(docstatus, grand, outstanding):
	if docstatus == 0:
		return "Draft"
	if docstatus == 2:
		return "Cancelled"
	if outstanding <= 0.01 and grand > 0:
		return "Paid"
	if grand - outstanding > 0.01:
		return "Partly Paid"
	return "Unpaid"


@frappe.whitelist()
def payables_summary(company=None):
	"""Header totals for the Bills panel (matches the prototype): outstanding Payable,
	Retention held (withheld on non-final subcontractor bills), and supplier Advances paid."""
	company = company or default_company()
	total = sum(flt(r["outstanding"]) for r in list_payables(company))
	retention = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(retention_amount), 0)
		FROM `tabSubcontractor Bill`
		WHERE docstatus = 1 AND company = %(company)s AND bill_type != 'Final'
		""",
		{"company": company},
	)
	advances = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(unallocated_amount), 0)
		FROM `tabPayment Entry`
		WHERE docstatus = 1 AND payment_type = 'Pay' AND party_type = 'Supplier'
			AND company = %(company)s AND unallocated_amount > 0
		""",
		{"company": company},
	)
	return {
		"outstanding": total,
		"retention": flt(retention[0][0]) if retention else 0,
		"advances": flt(advances[0][0]) if advances else 0,
	}


@frappe.whitelist()
def list_billable_purchase_orders(company=None):
	"""Submitted Purchase Orders that still have something to bill (per_billed < 100) — the
	'From Purchase Order' picker. A supplier bill raised against one pre-fills from its lines."""
	company = company or default_company()
	return frappe.get_all(
		"Purchase Order",
		filters={
			"docstatus": 1,
			"company": company,
			"status": ["not in", ["Closed", "Cancelled"]],
			"per_billed": ["<", 100],
		},
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"project",
			"transaction_date",
			"grand_total",
			"per_billed",
		],
		order_by="transaction_date desc, name desc",
	)


@frappe.whitelist()
def get_po_bill_lines(purchase_order):
	"""Confirm-don't-construct: map a Purchase Order to its unbilled bill lines (item, remaining
	qty, uom, PO rate) via ERPNext's native mapper, so the covered PO lines flip billed on submit.
	Returns the supplier + project too, to lock the bill header to the PO."""
	# ERPNext moved make_purchase_invoice into a `mapper` submodule in newer versions;
	# older versions keep it in purchase_order.py. Support both.
	try:
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
	except ModuleNotFoundError:
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

	po = frappe.get_doc("Purchase Order", purchase_order)
	po.check_permission("read")
	mapped = make_purchase_invoice(purchase_order)  # unsaved Purchase Invoice, unbilled qty only
	lines = [
		{
			"item_code": it.item_code,
			"description": it.item_name or it.description,
			"qty": flt(it.qty),
			"uom": it.uom,
			"rate": flt(it.rate),
			"purchase_order": it.get("purchase_order") or purchase_order,
			"po_detail": it.get("po_detail"),
		}
		for it in mapped.items
		if flt(it.qty) > 0
	]
	return {
		"purchase_order": po.name,
		"supplier": po.supplier,
		"supplier_name": po.supplier_name,
		"project": po.project,
		"lines": lines,
	}


@frappe.whitelist()
def get_item_details(item_code):
	"""Item master defaults for a direct bill line — the item name, its stock UOM and a buying
	rate (Item Price buying list, else last purchase rate) to pre-fill qty × rate."""
	it = frappe.db.get_value("Item", item_code, ["item_name", "stock_uom", "description"], as_dict=True) or {}
	rate = frappe.db.get_value("Item Price", {"item_code": item_code, "buying": 1}, "price_list_rate") or 0
	if not rate:
		rate = frappe.db.get_value("Item", item_code, "last_purchase_rate") or 0
	return {
		"item_name": it.get("item_name"),
		"uom": it.get("stock_uom"),
		"rate": flt(rate),
		"description": it.get("item_name") or it.get("description"),
	}


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def save_bill(payload):
	"""Create or edit a DRAFT supplier Purchase Invoice. Same shape as the customer invoice,
	plus an optional supplier bill_no/bill_date (the supplier's own reference)."""
	data = frappe.parse_json(payload)

	supplier = data.get("supplier")
	if not supplier:
		frappe.throw(_("Supplier is required."))
	items = data.get("items") or []
	if not items:
		frappe.throw(_("Add at least one bill line."))

	project = data.get("project")
	company = _company_for(project)

	name = data.get("name")
	if name and frappe.db.exists(PI, name):
		pi = frappe.get_doc(PI, name)
		pi.check_permission("write")
		if pi.docstatus != 0:
			frappe.throw(_("Only a draft bill can be edited."))
		pi.set("items", [])
		pi.set("taxes", [])
	else:
		pi = frappe.new_doc(PI)

	pi.company = company
	pi.supplier = supplier
	pi.currency = frappe.db.get_value("Company", company, "default_currency")
	pi.set_posting_time = 1
	pi.posting_date = data.get("date") or nowdate()
	pi.bill_no = data.get("bill_no") or None
	pi.bill_date = data.get("bill_date") or None
	pi.due_date = data.get("due_date") or pi.posting_date
	pi.project = project or None
	pi.update_stock = 0

	fallback_item = ensure_bill_item()
	expense = _expense_account(company)
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	for r in items:
		qty = flt(r.get("qty")) or 1
		# Real Item when the line carries one (Item picker / PO prefill); else the generic
		# service item, with the free-text detail on the description (backward compatible).
		line_item = r.get("item_code") or fallback_item
		row = {
			"item_code": line_item,
			"description": r.get("description")
			or frappe.db.get_value("Item", line_item, "item_name")
			or SERVICE_ITEM,
			"qty": qty,
			"rate": flt(r.get("rate")),
			"expense_account": expense,
			"cost_center": cost_center,
			"project": project or None,
		}
		if r.get("uom"):
			row["uom"] = r.get("uom")
		# Link back to the Purchase Order line so ERPNext tracks billed qty on the PO.
		if r.get("purchase_order") and r.get("po_detail"):
			row["purchase_order"] = r.get("purchase_order")
			row["po_detail"] = r.get("po_detail")
		pi.append("items", row)

	pi.taxes_and_charges = data.get("taxes_and_charges") or None
	rows = data.get("taxes")
	if rows is None and pi.taxes_and_charges:
		rows = get_tax_template_rows(pi.taxes_and_charges)
	for t in rows or []:
		if not t.get("account_head"):
			continue
		pi.append(
			"taxes",
			{
				"charge_type": t.get("charge_type") or "On Net Total",
				"account_head": t.get("account_head"),
				"description": t.get("description") or t.get("account_head"),
				"rate": flt(t.get("rate")),
				"category": "Total",
				"add_deduct_tax": "Add",
			},
		)

	pi.apply_discount_on = data.get("additional_discount_on") or "Net Total"
	pi.additional_discount_percentage = flt(data.get("additional_discount_percentage"))
	pi.discount_amount = flt(data.get("discount_amount"))
	pi.tc_name = data.get("tc_name") or None
	pi.terms = data.get("terms") or None

	for t in pi.taxes:
		if t.account_head and frappe.db.get_value("Account", t.account_head, "company") != company:
			frappe.throw(_("Tax account {0} does not belong to company {1}.").format(t.account_head, company))

	pi.flags.ignore_permissions = True
	pi.set_missing_values()
	pi.save()
	return {"name": pi.name}


@frappe.whitelist()
def submit_bill(name):
	pi = frappe.get_doc(PI, name)
	pi.check_permission("submit")
	pi.flags.ignore_permissions = True
	pi.submit()
	return {"name": pi.name, "payment": _payment_summary(name)}


@frappe.whitelist()
def cancel_bill(name):
	pi = frappe.get_doc(PI, name)
	pi.check_permission("cancel")
	pi.flags.ignore_permissions = True
	pi.cancel()
	return {"name": name, "cancelled": True}


@frappe.whitelist()
def delete_bill(name):
	pi = frappe.get_doc(PI, name)
	pi.check_permission("delete")
	if pi.docstatus != 0:
		frappe.throw(_("Only a draft bill can be deleted."))
	frappe.delete_doc(PI, name)
	return {"name": name, "deleted": True}


# --------------------------------------------------------------------------- #
# Pay (Payment Entry against the PI)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def record_payment(name, amount=None, date=None, mode_of_payment=None, pay_from=None, reference_no=None):
	"""Create + submit a Payment Entry paying the bill FROM a Bank/Cash account."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pi = frappe.get_doc(PI, name)
	pi.check_permission("write")
	if pi.docstatus != 1:
		frappe.throw(_("Submit the bill before paying it."))

	pe = get_payment_entry(PI, name)
	if date:
		pe.posting_date = date
	if pay_from:
		if frappe.db.get_value("Account", pay_from, "company") != pe.company:
			frappe.throw(_("Account {0} does not belong to company {1}.").format(pay_from, pe.company))
		pe.paid_from = pay_from
		pe.paid_from_account_currency = frappe.db.get_value("Account", pay_from, "account_currency")
	if amount:
		pe.paid_amount = flt(amount)
		pe.received_amount = flt(amount)
		if pe.references:
			pe.references[0].allocated_amount = flt(amount)
	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment
	if reference_no:
		pe.reference_no = reference_no
		pe.reference_date = date or nowdate()
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.submit()
	return {"payment_entry": pe.name, "payment": _payment_summary(name)}


@frappe.whitelist()
def list_payments(name):
	"""Cash payments allocated to this bill — plain Payment Entries only. Adjusted supplier
	advances are excluded here; they show under the bill's Advance Payments instead."""
	doc = frappe.get_doc(PI, name)
	advance_pes = {a["payment_entry"] for a in _linked_advances(doc)}
	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": PI, "reference_name": name, "docstatus": 1},
		fields=["parent", "allocated_amount"],
	)
	out = []
	for r in refs:
		if r.parent in advance_pes:
			continue
		pe = frappe.db.get_value(
			PE, r.parent, ["posting_date", "mode_of_payment", "reference_no"], as_dict=True
		)
		if not pe:
			continue
		out.append(
			{
				"payment_entry": r.parent,
				"date": str(pe.posting_date) if pe.posting_date else None,
				"mode_of_payment": pe.mode_of_payment,
				"reference_no": pe.reference_no,
				"amount": flt(r.allocated_amount),
			}
		)
	return out


@frappe.whitelist()
def record_advance(supplier, amount, date=None, pay_from=None, mode_of_payment=None, reference_no=None):
	"""Pay a supplier an advance BEFORE (or without) a bill — a submitted on-account Payment
	Entry whose full amount stays unallocated until a later bill draws it down."""
	from erpnext.accounts.party import get_party_account

	if not supplier:
		frappe.throw(_("Supplier is required."))
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter an amount greater than zero."))
	if not pay_from:
		frappe.throw(_("Choose the Bank/Cash account to pay from."))

	company = default_company()
	if frappe.db.get_value("Account", pay_from, "company") != company:
		frappe.throw(_("Account {0} does not belong to company {1}.").format(pay_from, company))

	payable = get_party_account("Supplier", supplier, company)
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Pay"
	pe.company = company
	pe.posting_date = date or nowdate()
	pe.party_type = "Supplier"
	pe.party = supplier
	pe.party_account = payable
	pe.paid_to = payable
	pe.paid_to_account_currency = frappe.db.get_value("Account", payable, "account_currency")
	pe.paid_from = pay_from
	pe.paid_from_account_currency = frappe.db.get_value("Account", pay_from, "account_currency")
	pe.paid_amount = amount
	pe.received_amount = amount
	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment
	if reference_no:
		pe.reference_no = reference_no
		pe.reference_date = date or nowdate()
	pe.flags.ignore_permissions = True
	pe.set_missing_values()
	pe.insert()
	pe.submit()
	return {"payment_entry": pe.name}


# --------------------------------------------------------------------------- #
# Adjust a supplier advance against a bill (ERPNext-native)
#   Draft     → the Purchase Invoice `advances` child table (reconciles on submit).
#   Submitted → Payment Reconciliation (link) / Unreconcile Payment (unlink).
# --------------------------------------------------------------------------- #
def _payable_for(supplier, company):
	from erpnext.accounts.party import get_party_account

	return get_party_account("Supplier", supplier, company)


def _draft_committed(pe_names):
	"""How much of each Payment Entry is already earmarked on DRAFT bills' advances tables. A
	draft advance does not reduce the Payment Entry's `unallocated_amount`, so we net it off
	ourselves — otherwise an advance already linked on a draft keeps showing as fully available
	and can be linked again and again."""
	if not pe_names:
		return {}
	rows = frappe.get_all(
		"Purchase Invoice Advance",
		filters={"reference_type": PE, "reference_name": ["in", list(pe_names)], "docstatus": 0},
		fields=["reference_name", "allocated_amount"],
	)
	out = {}
	for r in rows:
		out[r.reference_name] = out.get(r.reference_name, 0) + flt(r.allocated_amount)
	return out


@frappe.whitelist()
def available_advances(name):
	"""The bill supplier's on-account advances that can still be adjusted against this bill,
	oldest first — the Payment Entry's unallocated balance net of anything already earmarked on
	any draft bill (including this one)."""
	pi = frappe.get_doc(PI, name)
	pi.check_permission("read")
	rows = frappe.get_all(
		PE,
		filters={
			"docstatus": 1,
			"payment_type": "Pay",
			"party_type": "Supplier",
			"party": pi.supplier,
			"company": pi.company,
			"unallocated_amount": [">", 0.01],
		},
		fields=["name", "posting_date", "unallocated_amount", "mode_of_payment", "reference_no", "paid_from"],
		order_by="posting_date asc, creation asc",
	)
	committed = _draft_committed([r.name for r in rows])
	out = []
	for r in rows:
		remaining = flt(r.unallocated_amount) - flt(committed.get(r.name, 0))
		if remaining <= 0.01:
			continue
		out.append(
			{
				"payment_entry": r.name,
				"date": str(r.posting_date) if r.posting_date else None,
				"unallocated": remaining,
				"mode_of_payment": r.mode_of_payment,
				"reference_no": r.reference_no,
				"pay_from": r.paid_from,
			}
		)
	return out


def _reconcile_advance(pi, pe, amount):
	"""Allocate `amount` of an unallocated advance Payment Entry against a submitted bill via the
	native Payment Reconciliation tool (honours a partial allocation)."""
	pr = frappe.new_doc("Payment Reconciliation")
	pr.company = pi.company
	pr.party_type = "Supplier"
	pr.party = pi.supplier
	pr.receivable_payable_account = _payable_for(pi.supplier, pi.company)
	pr.get_unreconciled_entries()
	inv_d = [i.as_dict() for i in pr.invoices if i.invoice_number == pi.name]
	pay_d = [p.as_dict() for p in pr.payments if p.reference_name == pe.name]
	if not inv_d or not pay_d:
		frappe.throw(_("Could not find the advance or the bill among unreconciled entries."))
	pr.allocate_entries({"invoices": inv_d, "payments": pay_d})
	matched = False
	for a in pr.allocation:
		if a.reference_name == pe.name and a.invoice_number == pi.name:
			a.allocated_amount = amount
			matched = True
		else:
			a.allocated_amount = 0
	pr.set("allocation", [a for a in pr.allocation if flt(a.allocated_amount) > 0])
	if not matched or not pr.allocation:
		frappe.throw(_("Allocation could not be prepared."))
	pr.reconcile()


@frappe.whitelist()
def link_advance(name, payment_entry, amount):
	"""Adjust `amount` of a supplier advance against this bill, reducing its outstanding."""
	pi = frappe.get_doc(PI, name)
	pi.check_permission("write")
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter an allocation greater than zero."))

	pe = frappe.get_doc(PE, payment_entry)
	if pe.docstatus != 1 or pe.payment_type != "Pay" or pe.party != pi.supplier:
		frappe.throw(_("{0} is not an advance to this supplier.").format(payment_entry))
	available = flt(pe.unallocated_amount)
	if amount > available + 0.01:
		frappe.throw(_("Only {0} is unadjusted on {1}.").format(available, payment_entry))

	if pi.docstatus == 0:
		existing = next(
			(a for a in pi.advances if a.reference_type == PE and a.reference_name == payment_entry), None
		)
		prior = flt(existing.allocated_amount) if existing else 0
		other_rows = sum(flt(a.allocated_amount) for a in pi.advances if a is not existing)
		committed_elsewhere = flt(_draft_committed([payment_entry]).get(payment_entry, 0)) - prior
		pe_room = available - committed_elsewhere - prior
		bill_room = flt(pi.grand_total) - other_rows - prior
		room = min(pe_room, bill_room)
		if room <= 0.01:
			frappe.throw(_("This advance is already fully adjusted against the bill."))
		if amount > room + 0.01:
			frappe.throw(
				_("At most {0} more of {1} can be adjusted against this bill.").format(room, payment_entry)
			)
		if existing:
			existing.advance_amount = available
			existing.allocated_amount = prior + amount
		else:
			pi.append(
				"advances",
				{
					"reference_type": PE,
					"reference_name": payment_entry,
					"advance_amount": available,
					"allocated_amount": amount,
					"remarks": pe.remarks,
				},
			)
		pi.flags.ignore_permissions = True
		pi.save()
	elif pi.docstatus == 1:
		if flt(pi.outstanding_amount) <= 0.01:
			frappe.throw(_("This bill is already settled."))
		_reconcile_advance(pi, pe, min(amount, flt(pi.outstanding_amount)))
	else:
		frappe.throw(_("A cancelled bill cannot take advances."))
	return {"payment": _payment_summary(name)}


@frappe.whitelist()
def unlink_advance(name, payment_entry):
	"""Reverse an advance adjustment — remove the draft `advances` row, or unreconcile the
	Payment Entry from a submitted bill (native Unreconcile Payment)."""
	pi = frappe.get_doc(PI, name)
	pi.check_permission("write")
	if pi.docstatus == 0:
		pi.set(
			"advances",
			[a for a in pi.advances if not (a.reference_type == PE and a.reference_name == payment_entry)],
		)
		pi.flags.ignore_permissions = True
		pi.save()
	elif pi.docstatus == 1:
		from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import (
			create_unreconcile_doc_for_selection,
		)

		create_unreconcile_doc_for_selection(
			frappe.as_json(
				[
					{
						"company": pi.company,
						"voucher_type": PE,
						"voucher_no": payment_entry,
						"against_voucher_type": PI,
						"against_voucher_no": pi.name,
					}
				]
			)
		)
	else:
		frappe.throw(_("Nothing to unlink on a cancelled bill."))
	return {"payment": _payment_summary(name)}


# --------------------------------------------------------------------------- #
# Pickers
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def list_pay_accounts(company=None):
	"""Bank/Cash accounts a bill can be paid FROM — the active (default) company."""
	company = company or default_company()
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_type"],
		order_by="account_type, name",
	)


@frappe.whitelist()
def list_tax_templates(company=None):
	filters = {"disabled": 0}
	if company:
		filters["company"] = company
	return frappe.get_all(
		"Purchase Taxes and Charges Template", filters=filters, fields=["name", "title"], order_by="title asc"
	)


@frappe.whitelist()
def get_tax_template_rows(template):
	doc = frappe.get_doc("Purchase Taxes and Charges Template", template)
	return [
		{
			"charge_type": t.charge_type,
			"account_head": t.account_head,
			"description": t.description or t.account_head,
			"rate": t.rate,
		}
		for t in doc.taxes
	]


@frappe.whitelist()
def get_terms(name):
	from buildsuite_core.api.invoice import _html_to_text

	return {"terms": _html_to_text(frappe.db.get_value("Terms and Conditions", name, "terms"))}


@frappe.whitelist()
def list_payment_modes():
	return frappe.get_all("Mode of Payment", fields=["name"], order_by="name", pluck="name")
