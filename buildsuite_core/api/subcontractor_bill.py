# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Subcontractor Bill — the Vue front-end of the bill DocType.

Two modes: a Work Order bill (lines derived from certified Measurement Books) and a Direct
bill (free-text charge lines). Submit generates a linked Purchase Invoice; payment is a real
ERPNext Payment Entry against that PI. Taxes are country-agnostic (any Purchase Taxes and
Charges Template)."""

import frappe
from frappe import _
from frappe.utils import flt

BILL = "Subcontractor Bill"
WORK_ORDER = "Subcontractor Work Order"


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #
def _serialize(doc):
	return {
		"name": doc.name,
		"is_direct": doc.is_direct,
		"work_order": doc.work_order,
		"ra_no": doc.ra_no,
		"subcontractor": doc.subcontractor,
		"subcontractor_name": doc.subcontractor_name,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"company": doc.company,
		"date": str(doc.date) if doc.date else None,
		"bill_type": doc.bill_type,
		"retention_percent": doc.retention_percent,
		"status": doc.status,
		"docstatus": doc.docstatus,
		"taxes_and_charges": doc.taxes_and_charges,
		"tax_category": doc.tax_category,
		"apply_tds": doc.apply_tds,
		"tax_withholding_category": doc.tax_withholding_category,
		"tds_rate": doc.tds_rate,
		"additional_discount_on": doc.additional_discount_on,
		"additional_discount_percentage": doc.additional_discount_percentage,
		"discount_amount": doc.discount_amount,
		"advance_recovery": doc.advance_recovery,
		"expense_account": doc.expense_account,
		# Totals waterfall
		"gross": doc.gross,
		"taxable_value": doc.taxable_value,
		"total_taxes": doc.total_taxes,
		"grand_total": doc.grand_total,
		"tds_amount": doc.tds_amount,
		"retention_amount": doc.retention_amount,
		"invoice_value": doc.invoice_value,
		"net_payable": doc.net_payable,
		"purchase_invoice": doc.purchase_invoice,
		"amended_from": doc.amended_from,
		"lines": [
			{
				"name": r.name,
				"work_order_line": r.work_order_line,
				"scope": r.scope,
				"cost_code_type": r.cost_code_type,
				"cost_code_group": r.cost_code_group,
				"cost_code_item": r.cost_code_item,
				"cost_code_label": r.cost_code_label,
				"uom": r.uom,
				"rate": r.rate,
				"measured_qty_to_date": r.measured_qty_to_date,
				"previous_qty": r.previous_qty,
				"this_period_qty": r.this_period_qty,
				"this_period_amount": r.this_period_amount,
			}
			for r in doc.lines
		],
		"taxes": [
			{
				"name": t.name,
				"charge_type": t.charge_type,
				"account_head": t.account_head,
				"description": t.description,
				"rate": t.rate,
				"tax_amount": t.tax_amount,
			}
			for t in doc.taxes
		],
		"payment": _payment_summary(doc),
		"actions": _available_actions(doc),
	}


def _available_actions(doc):
	if doc.docstatus == 0:
		return ["submit", "delete"]
	if doc.docstatus == 1:
		acts = []
		if _payment_summary(doc)["outstanding"] > 0.01:
			acts.append("pay")
		acts.append("cancel")
		return acts
	return []


def _payment_summary(doc):
	"""Read payment state THROUGH the generated PI (the bill stores none of its own)."""
	if not doc.purchase_invoice or not frappe.db.exists("Purchase Invoice", doc.purchase_invoice):
		return {"invoiced": 0, "paid": 0, "outstanding": 0, "status": "Unpaid"}
	pi = frappe.db.get_value(
		"Purchase Invoice", doc.purchase_invoice, ["grand_total", "outstanding_amount", "status"], as_dict=True
	)
	invoiced = flt(pi.grand_total)
	outstanding = flt(pi.outstanding_amount)
	paid = invoiced - outstanding
	if outstanding <= 0.01 and invoiced > 0:
		status = "Paid"
	elif paid > 0.01:
		status = "Partly Paid"
	else:
		status = "Unpaid"
	return {"invoiced": invoiced, "paid": paid, "outstanding": outstanding, "status": status}


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_bill(name: str):
	doc = frappe.get_doc(BILL, name)
	doc.check_permission("read")
	return _serialize(doc)


@frappe.whitelist()
def get_wo_bill_context(work_order: str):
	"""Everything the New (Work Order) bill screen needs: WO header, the derived this-period
	lines (measured − previously billed), and the next RA number."""
	from buildsuite_core.api.subcontract import get_wo_measurements
	from buildsuite_core.buildsuite_core.doctype.subcontractor_bill.subcontractor_bill import (
		previously_billed_by_line,
	)

	wo = frappe.get_doc(WORK_ORDER, work_order)
	wo.check_permission("read")
	measured = get_wo_measurements(work_order).get("measured_by_line", {})
	previous = previously_billed_by_line(work_order)

	lines = []
	for row in wo.lines:
		m = flt(measured.get(row.name, 0))
		p = flt(previous.get(row.name, 0))
		tpq = max(0.0, m - p)
		lines.append(
			{
				"work_order_line": row.name,
				"scope": row.scope,
				"cost_code_label": row.cost_code_label,
				"uom": row.uom,
				"rate": row.rate,
				"measured_qty_to_date": m,
				"previous_qty": p,
				"this_period_qty": tpq,
				"this_period_amount": tpq * flt(row.rate),
			}
		)
	existing = frappe.get_all(
		BILL, filters={"work_order": work_order, "docstatus": ["<", 2]}, pluck="ra_no"
	)
	return {
		"work_order": wo.name,
		"subcontractor": wo.subcontractor,
		"subcontractor_name": wo.subcontractor_name,
		"project": wo.project,
		"project_name": frappe.db.get_value("Project", wo.project, "project_name"),
		"company": wo.company,
		"retention_percent": wo.retention_percent,
		"status": wo.status,
		"total_value": wo.total_value,
		"next_ra_no": max([r for r in existing if r] or [0]) + 1,
		"lines": lines,
	}


@frappe.whitelist()
def list_tax_templates(company: str | None = None):
	"""Purchase Taxes and Charges Templates for the picker — dynamic, whatever the site's
	compliance app has seeded (GST, VAT, none). Not GST-specific."""
	filters = {"disabled": 0}
	if company:
		filters["company"] = company
	return frappe.get_all(
		"Purchase Taxes and Charges Template", filters=filters, fields=["name", "title"], order_by="title asc"
	)


@frappe.whitelist()
def get_tax_template_rows(template: str):
	"""Resolve a template's tax rows into the bill's tax-table shape."""
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
def list_withholding_categories():
	return frappe.get_all("Tax Withholding Category", fields=["name"], order_by="name asc")


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def save_bill(payload):
	"""Create or update a DRAFT bill (both modes). WO-bill lines are re-derived server-side
	from the Measurement Books (never trusted from the client); direct-bill lines are taken
	from the payload."""
	data = frappe.parse_json(payload)
	name = data.get("name")

	if name and frappe.db.exists(BILL, name):
		doc = frappe.get_doc(BILL, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft bill can be edited."))
	else:
		doc = frappe.new_doc(BILL)

	doc.is_direct = 1 if data.get("is_direct") else 0
	doc.date = data.get("date")
	doc.bill_type = data.get("bill_type") or "Normal"

	if doc.is_direct:
		doc.work_order = None
		doc.subcontractor = data.get("subcontractor")
		doc.project = data.get("project")
		doc.retention_percent = flt(data.get("retention_percent"))
		doc.set("lines", [])
		for row in data.get("lines") or []:
			amount = flt(row.get("amount") if row.get("amount") is not None else row.get("this_period_amount"))
			if not (row.get("scope") or "").strip() and amount <= 0:
				continue
			doc.append(
				"lines",
				{
					"scope": (row.get("scope") or "").strip(),
					"cost_code_label": row.get("cost_code_label") or row.get("cost_code") or "",
					"this_period_amount": amount,
				},
			)
	else:
		doc.work_order = data.get("work_order")
		if data.get("retention_percent") not in (None, ""):
			doc.retention_percent = flt(data.get("retention_percent"))
		doc.fetch_lines()  # re-derive lines from certified MBs

	# Billing block.
	doc.taxes_and_charges = data.get("taxes_and_charges")
	doc.tax_category = data.get("tax_category")
	doc.apply_tds = 1 if data.get("apply_tds") else 0
	doc.tax_withholding_category = data.get("tax_withholding_category")
	doc.additional_discount_on = data.get("additional_discount_on") or "Net Total"
	doc.additional_discount_percentage = flt(data.get("additional_discount_percentage"))
	doc.discount_amount = flt(data.get("discount_amount"))
	doc.advance_recovery = flt(data.get("advance_recovery"))
	if "expense_account" in data:
		doc.expense_account = data.get("expense_account")

	# Taxes: explicit rows if given, else expand the chosen template.
	rows = data.get("taxes")
	if rows is None and doc.taxes_and_charges:
		rows = get_tax_template_rows(doc.taxes_and_charges)
	doc.set("taxes", [])
	for t in rows or []:
		doc.append(
			"taxes",
			{
				"charge_type": t.get("charge_type") or "On Net Total",
				"account_head": t.get("account_head"),
				"description": t.get("description"),
				"rate": flt(t.get("rate")),
			},
		)

	doc.flags.ignore_permissions = True
	doc.save()
	return _serialize(doc)


@frappe.whitelist()
def submit_bill(name: str):
	doc = frappe.get_doc(BILL, name)
	doc.check_permission("submit")
	doc.submit()
	return _serialize(doc)


@frappe.whitelist()
def cancel_bill(name: str):
	doc = frappe.get_doc(BILL, name)
	doc.check_permission("cancel")
	doc.cancel()
	return _serialize(doc)


@frappe.whitelist()
def delete_bill(name: str):
	doc = frappe.get_doc(BILL, name)
	doc.check_permission("delete")
	if doc.docstatus == 1:
		frappe.throw(_("Cancel a submitted bill before deleting it."))
	frappe.delete_doc(BILL, name)
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Payment (real ERPNext Payment Entry against the generated PI)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def record_payment(name, amount=None, date=None, mode_of_payment=None, paid_from=None, reference_no=None):
	"""Create + submit a Payment Entry against the bill's Purchase Invoice."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	bill = frappe.get_doc(BILL, name)
	bill.check_permission("write")
	if not bill.purchase_invoice:
		frappe.throw(_("This bill has no Purchase Invoice yet — submit it first."))

	pe = get_payment_entry("Purchase Invoice", bill.purchase_invoice)
	if date:
		pe.posting_date = date
	if amount:
		pe.paid_amount = flt(amount)
		pe.received_amount = flt(amount)
		if pe.references:
			pe.references[0].allocated_amount = flt(amount)
	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment
	if reference_no:
		pe.reference_no = reference_no
		pe.reference_date = date or bill.date
	pe.flags.ignore_permissions = True
	pe.insert()
	pe.submit()
	return {"payment_entry": pe.name, "payment": _payment_summary(frappe.get_doc(BILL, name))}


@frappe.whitelist()
def list_payments(name: str):
	"""Payment Entries allocated to this bill's PI."""
	bill = frappe.db.get_value(BILL, name, "purchase_invoice")
	if not bill:
		return []
	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Purchase Invoice", "reference_name": bill, "docstatus": 1},
		fields=["parent", "allocated_amount"],
	)
	out = []
	for r in refs:
		pe = frappe.db.get_value(
			"Payment Entry", r.parent, ["posting_date", "mode_of_payment", "reference_no"], as_dict=True
		)
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
