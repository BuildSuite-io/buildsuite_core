# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Payments — a unified register of party payments over ERPNext Payment
Entries. Every invoice receipt, customer/supplier/subcontractor advance, bill payment and
subcontractor payment IS a Payment Entry; this classifies each by direction (money in/out) and
a friendly movement type, and cancels (reverses) one on request. Petty-cash disbursements are
NOT payments (internal float transfer) — they live under Petty Cash. Single-company for now."""

import frappe
from frappe import _
from frappe.utils import flt

from buildsuite_core.utils.project import default_company

PE = "Payment Entry"
PI = "Purchase Invoice"
SUPPLIER = "Supplier"


def _subcontractor_suppliers():
	return set(frappe.get_all(SUPPLIER, filters={"supplier_type": "Subcontractor"}, pluck="name"))


def _classify(pe, refs, sub_suppliers):
	"""Derive (movement type, direction, bank/cash account, reference) for a Payment Entry.
	Receive → money in (customer receipt/advance); Pay → money out (bill/advance/subcontractor)."""
	allocated = sum(flt(r.allocated_amount) for r in refs)
	ref_name = refs[0].reference_name if refs else None

	if pe.payment_type == "Receive":
		movement = "Invoice receipt" if allocated > 0.01 else "Customer advance"
		return movement, "in", pe.paid_to, ref_name

	# Pay
	if allocated > 0.01:
		pi_ref = next((r.reference_name for r in refs if r.reference_doctype == PI), None)
		sub_bill = frappe.db.get_value(PI, pi_ref, "subcontractor_bill") if pi_ref else None
		if sub_bill:
			return "Subcontractor payment", "out", pe.paid_from, sub_bill
		return "Bill payment", "out", pe.paid_from, ref_name
	movement = "Subcontractor advance" if pe.party in sub_suppliers else "Supplier advance"
	return movement, "out", pe.paid_from, ref_name


@frappe.whitelist()
def list_payments(company=None):
	"""Every submitted party Payment Entry for the active (default) company, newest first."""
	company = company or default_company()
	pes = frappe.get_all(
		PE,
		filters={
			"docstatus": 1,
			"company": company,
			"payment_type": ["in", ["Receive", "Pay"]],
			"party_type": ["in", ["Customer", SUPPLIER]],
		},
		fields=[
			"name",
			"payment_type",
			"party_type",
			"party",
			"party_name",
			"posting_date",
			"paid_amount",
			"paid_from",
			"paid_to",
			"mode_of_payment",
			"reference_no",
		],
		order_by="posting_date desc, creation desc",
	)
	if not pes:
		return []

	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"parent": ["in", [p.name for p in pes]], "docstatus": 1},
		fields=["parent", "reference_doctype", "reference_name", "allocated_amount"],
	)
	refs_by_pe = {}
	for r in refs:
		refs_by_pe.setdefault(r.parent, []).append(r)

	sub_suppliers = _subcontractor_suppliers()
	out = []
	for p in pes:
		movement, direction, account, ref_name = _classify(p, refs_by_pe.get(p.name, []), sub_suppliers)
		out.append(
			{
				"name": p.name,
				"date": str(p.posting_date) if p.posting_date else None,
				"type": movement,
				"party": p.party_name or p.party,
				"account": account,
				"dir": direction,
				"amount": flt(p.paid_amount),
				"mode_of_payment": p.mode_of_payment,
				"reference_no": p.reference_no,
				"ref": ref_name,
			}
		)
	return out


@frappe.whitelist()
def cancel_payment(name):
	"""Cancel (reverse) a Payment Entry. ERPNext discipline: posted transactions are cancelled,
	not edited — the linked invoice/bill outstanding (or the party's unallocated advance)
	recomputes automatically. Record a fresh payment if it was entered wrongly."""
	pe = frappe.get_doc(PE, name)
	pe.check_permission("cancel")
	pe.flags.ignore_permissions = True
	pe.cancel()
	return {"name": name, "cancelled": True}
