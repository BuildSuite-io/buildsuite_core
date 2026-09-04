# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for Project Finance › Invoices — the Vue front-end over ERPNext's
Sales Invoice (money in). An "invoice" IS a Sales Invoice: these endpoints create drafts,
list them with aging, submit/cancel, and receive payments (a real Payment Entry against the
SI). Single-company for now — the company is the project's, else the default (see the
single-company seam). Taxes are country-agnostic (any Sales Taxes and Charges Template)."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from buildsuite_core.utils.project import default_company

SI = "Sales Invoice"
PE = "Payment Entry"
SERVICE_ITEM = "Professional Services"
SERVICE_ITEM_GROUP = "Services"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _company_for(project=None):
	if project:
		return frappe.db.get_value("Project", project, "company") or default_company()
	return default_company()


def ensure_invoice_item():
	"""A generic non-stock sales Item that invoice lines hang off (the description carries the
	real detail). Mirrors the Subcontractor Bill's service-item approach."""
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
			"is_sales_item": 1,
			"is_purchase_item": 0,
		}
	).insert(ignore_permissions=True)
	return SERVICE_ITEM


def _income_account(company):
	acc = frappe.db.get_value("Company", company, "default_income_account")
	if acc:
		return acc
	from buildsuite_core.utils.subcontract_billing import _ensure_account

	return _ensure_account(company, "Sales", "Income", "Income Account", "Income")


def _payment_summary(name):
	si = frappe.db.get_value(
		SI, name, ["grand_total", "outstanding_amount", "status", "docstatus"], as_dict=True
	)
	if not si or si.docstatus == 0:
		return {"invoiced": 0, "received": 0, "outstanding": 0, "status": "Draft"}
	invoiced = flt(si.grand_total)
	outstanding = flt(si.outstanding_amount)
	received = invoiced - outstanding
	if si.docstatus == 2:
		status = "Cancelled"
	elif outstanding <= 0.01 and invoiced > 0:
		status = "Paid"
	elif received > 0.01:
		status = "Partly Paid"
	else:
		status = "Unpaid"
	return {"invoiced": invoiced, "received": received, "outstanding": outstanding, "status": status}


def _ref_is_advance(pe_type, paid_amount, unallocated, allocated):
	"""True when a Payment Entry linked to an invoice is a customer ADVANCE (on-account money
	adjusted against the invoice) rather than a plain receipt raised for that one invoice. A
	receipt (via record_receipt) is a Receive fully consumed 1:1 by the invoice; an advance
	still carries unallocated money or funds more than this allocation."""
	if pe_type != "Receive":
		return False
	return flt(unallocated) > 0.01 or flt(paid_amount) - flt(allocated) > 0.01


def _linked_advances(doc):
	"""Advances adjusted against this invoice, one entry per Payment Entry with its TOTAL applied.

	Draft → the native `advances` table. Submitted → the advance's Payment Entry references to
	this invoice, SUMMED per Payment Entry (a partial advance may be reconciled in several steps,
	each adding its own reference row). A Payment Entry counts as an advance when it was set on
	the invoice before submit (its advances-table row is retained after submit) or when it is an
	on-account receipt reconciled after submit — a plain cash receipt is neither."""
	if doc.docstatus == 0:
		return [
			{"payment_entry": a.reference_name, "allocated": flt(a.allocated_amount)}
			for a in doc.advances
			if a.reference_type == PE and flt(a.allocated_amount) > 0
		]

	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": SI, "reference_name": doc.name, "docstatus": 1},
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
				PE,
				pe_name,
				["payment_type", "paid_amount", "unallocated_amount", "custom_is_bs_advance"],
				as_dict=True,
			)
			# The durable flag (set when the advance was recorded / linked) is authoritative;
			# fall back to the unallocated-leftover heuristic for legacy entries without it —
			# without the flag a fully-consumed advance is indistinguishable from a receipt.
			is_advance = bool(pe) and (
				pe.custom_is_bs_advance
				or _ref_is_advance(pe.payment_type, pe.paid_amount, pe.unallocated_amount, total)
			)
		if is_advance:
			out.append({"payment_entry": pe_name, "allocated": total})
	return out


def _serialize(doc):
	advances = _linked_advances(doc)
	adjusted = sum(a["allocated"] for a in advances)
	pay = _payment_summary(doc.name)
	# Advance adjustment settles the receivable but is not a cash receipt — split it out of
	# "Received" so the totals read the way the prototype shows them.
	pay["advance_adjusted"] = adjusted
	if doc.docstatus == 1:
		pay["received"] = max(flt(pay["received"]) - adjusted, 0)
	return {
		"name": doc.name,
		"customer": doc.customer,
		"customer_name": doc.customer_name,
		"customer_gstin": frappe.db.get_value("Customer", doc.customer, "tax_id") if doc.customer else None,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"company": doc.company,
		"date": str(doc.posting_date) if doc.posting_date else None,
		"due_date": str(doc.due_date) if doc.due_date else None,
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
		"total_advance": flt(doc.get("total_advance")),
		"advance_adjusted": adjusted,
		"advances": advances,
		"items": [
			{"description": r.description, "qty": r.qty, "rate": r.rate, "amount": r.amount}
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
def list_invoices(project: str | None = None, company: str | None = None):
	"""Sales Invoices for the active (default) company, newest first, with the payment summary
	for aging/status in the panel."""
	company = company or default_company()
	filters = {"company": company}
	if project:
		filters["project"] = project
	rows = frappe.get_all(
		SI,
		filters=filters,
		fields=[
			"name",
			"customer",
			"customer_name",
			"project",
			"posting_date",
			"due_date",
			"grand_total",
			"outstanding_amount",
			"status",
			"docstatus",
		],
		order_by="posting_date desc, creation desc",
		limit_page_length=0,
	)
	pids = list({r.project for r in rows if r.project})
	pnames = (
		{
			p.name: p.project_name
			for p in frappe.get_all(
				"Project", filters={"name": ["in", pids]}, fields=["name", "project_name"]
			)
		}
		if pids
		else {}
	)
	out = []
	for r in rows:
		invoiced = flt(r.grand_total)
		outstanding = flt(r.outstanding_amount) if r.docstatus == 1 else invoiced
		if r.docstatus == 0:
			pay_status = "Draft"
		elif r.docstatus == 2:
			pay_status = "Cancelled"
		elif outstanding <= 0.01 and invoiced > 0:
			pay_status = "Paid"
		elif invoiced - outstanding > 0.01:
			pay_status = "Partly Paid"
		else:
			pay_status = "Unpaid"
		out.append(
			{
				"name": r.name,
				"customer": r.customer,
				"customer_name": r.customer_name or r.customer,
				"project": r.project,
				"project_name": pnames.get(r.project) or r.project,
				"date": str(r.posting_date) if r.posting_date else None,
				"due_date": str(r.due_date) if r.due_date else None,
				"total": invoiced,
				"outstanding": outstanding if r.docstatus == 1 else 0,
				"docstatus": r.docstatus,
				"status": pay_status,
			}
		)
	return out


@frappe.whitelist()
def get_invoice(name: str):
	doc = frappe.get_doc(SI, name)
	doc.check_permission("read")
	return _serialize(doc)


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def save_invoice(payload: str):
	"""Create or edit a DRAFT Sales Invoice. payload: {name?, customer, project?, date,
	due_date?, items:[{description, qty, rate}], taxes_and_charges?, taxes:[{charge_type,
	account_head, rate, description}], additional_discount_on?, additional_discount_percentage?,
	discount_amount?, terms?, tc_name?}. Taxes/discount follow the Subcontractor Bill pattern."""
	data = frappe.parse_json(payload)

	customer = data.get("customer")
	if not customer:
		frappe.throw(_("Customer is required."))
	items = data.get("items") or []
	if not items:
		frappe.throw(_("Add at least one invoice line."))

	project = data.get("project")
	company = _company_for(project)

	name = data.get("name")
	if name and frappe.db.exists(SI, name):
		si = frappe.get_doc(SI, name)
		si.check_permission("write")
		if si.docstatus != 0:
			frappe.throw(_("Only a draft invoice can be edited."))
		si.set("items", [])
		si.set("taxes", [])
	else:
		si = frappe.new_doc(SI)

	si.company = company
	si.customer = customer
	si.currency = frappe.db.get_value("Company", company, "default_currency")
	si.set_posting_time = 1
	si.posting_date = data.get("date") or nowdate()
	si.due_date = data.get("due_date") or si.posting_date
	si.project = project or None

	item_code = ensure_invoice_item()
	income = _income_account(company)
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	for r in items:
		qty = flt(r.get("qty")) or 1
		si.append(
			"items",
			{
				"item_code": item_code,
				"description": r.get("description") or SERVICE_ITEM,
				"qty": qty,
				"rate": flt(r.get("rate")),
				"income_account": income,
				"cost_center": cost_center,
				"project": project or None,
			},
		)

	# Taxes: the edited rows if the UI sent any, else expand the chosen template (Bill pattern).
	si.taxes_and_charges = data.get("taxes_and_charges") or None
	rows = data.get("taxes")
	if rows is None and si.taxes_and_charges:
		rows = get_tax_template_rows(si.taxes_and_charges)
	for t in rows or []:
		if not t.get("account_head"):
			continue
		si.append(
			"taxes",
			{
				"charge_type": t.get("charge_type") or "On Net Total",
				"account_head": t.get("account_head"),
				"description": t.get("description") or t.get("account_head"),
				"rate": flt(t.get("rate")),
			},
		)

	# Discount → native SI fields (percentage OR amount, on Net/Grand Total).
	si.apply_discount_on = data.get("additional_discount_on") or "Net Total"
	si.additional_discount_percentage = flt(data.get("additional_discount_percentage"))
	si.discount_amount = flt(data.get("discount_amount"))

	# Terms & conditions.
	si.tc_name = data.get("tc_name") or None
	si.terms = data.get("terms") or None

	# Single-company guard: every tax account must belong to this invoice's company (else the
	# Sales Invoice rejects it with a cryptic row error).
	for t in si.taxes:
		if t.account_head and frappe.db.get_value("Account", t.account_head, "company") != company:
			frappe.throw(_("Tax account {0} does not belong to company {1}.").format(t.account_head, company))

	si.flags.ignore_permissions = True
	si.set_missing_values()
	si.save()
	return {"name": si.name}


def _guard_workflow():
	"""Once a site configures an active workflow for Sales Invoice, submission and
	cancellation must flow through it (buildsuite_core.api.workflow.apply_action), not
	these direct docstatus endpoints — otherwise the workflow_state and docstatus drift
	apart. The Vue detail view already routes to the workflow when one is active; this is
	the server-side backstop."""
	from buildsuite_core.api.workflow import workflow_active

	if workflow_active(SI):
		frappe.throw(_("Sales Invoice is governed by a workflow — use a workflow action."))


@frappe.whitelist()
def submit_invoice(name: str):
	_guard_workflow()
	si = frappe.get_doc(SI, name)
	si.check_permission("submit")
	si.flags.ignore_permissions = True
	si.submit()
	return {"name": si.name, "payment": _payment_summary(name)}


@frappe.whitelist()
def cancel_invoice(name: str):
	_guard_workflow()
	si = frappe.get_doc(SI, name)
	si.check_permission("cancel")
	si.flags.ignore_permissions = True
	si.cancel()
	return {"name": name, "cancelled": True}


@frappe.whitelist()
def delete_invoice(name: str):
	si = frappe.get_doc(SI, name)
	si.check_permission("delete")
	if si.docstatus != 0:
		frappe.throw(_("Only a draft invoice can be deleted."))
	frappe.delete_doc(SI, name)
	return {"name": name, "deleted": True}


# --------------------------------------------------------------------------- #
# Receive payment (Payment Entry against the SI)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def record_receipt(name: str, amount: float | int | str | None = None, date: str | None = None, mode_of_payment: str | None = None, deposit_to: str | None = None, reference_no: str | None = None):
	"""Create + submit a Payment Entry receiving against the invoice, into a Bank/Cash account."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	si = frappe.get_doc(SI, name)
	si.check_permission("write")
	if si.docstatus != 1:
		frappe.throw(_("Submit the invoice before receiving payment."))

	pe = get_payment_entry(SI, name)
	if date:
		pe.posting_date = date
	if deposit_to:
		if frappe.db.get_value("Account", deposit_to, "company") != pe.company:
			frappe.throw(_("Account {0} does not belong to company {1}.").format(deposit_to, pe.company))
		pe.paid_to = deposit_to
		pe.paid_to_account_currency = frappe.db.get_value("Account", deposit_to, "account_currency")
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
def list_receipts(name: str):
	"""Cash receipts allocated to this invoice — plain Payment Entries only. Adjusted customer
	advances are excluded here; they show under the invoice's Advance Payments instead."""
	doc = frappe.get_doc(SI, name)
	advance_pes = {a["payment_entry"] for a in _linked_advances(doc)}
	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": SI, "reference_name": name, "docstatus": 1},
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


# --------------------------------------------------------------------------- #
# Customer advances (on-account receipts, no invoice yet)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def record_advance(customer: str, amount: float | int | str, date: str | None = None, deposit_to: str | None = None, mode_of_payment: str | None = None, reference_no: str | None = None):
	"""Receive money from a customer BEFORE (or without) an invoice — a submitted on-account
	Payment Entry whose full amount stays unallocated until a later invoice draws it down."""
	from erpnext.accounts.party import get_party_account

	if not customer:
		frappe.throw(_("Customer is required."))
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter an amount greater than zero."))
	if not deposit_to:
		frappe.throw(_("Choose the Bank/Cash account to deposit into."))

	company = default_company()
	if frappe.db.get_value("Account", deposit_to, "company") != company:
		frappe.throw(_("Account {0} does not belong to company {1}.").format(deposit_to, company))

	receivable = get_party_account("Customer", customer, company)
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.company = company
	pe.posting_date = date or nowdate()
	pe.party_type = "Customer"
	pe.party = customer
	pe.party_account = receivable
	pe.paid_from = receivable
	pe.paid_from_account_currency = frappe.db.get_value("Account", receivable, "account_currency")
	pe.paid_to = deposit_to
	pe.paid_to_account_currency = frappe.db.get_value("Account", deposit_to, "account_currency")
	pe.paid_amount = amount
	pe.received_amount = amount
	if mode_of_payment:
		pe.mode_of_payment = mode_of_payment
	# ERPNext makes Reference No + Date mandatory for a Bank Mode of Payment; we keep them
	# OPTIONAL for the user by defaulting them when none was supplied (harmless for cash).
	pe.reference_no = reference_no or "Advance"
	pe.reference_date = date or nowdate()
	pe.custom_is_bs_advance = 1  # durable marker — a fully-consumed advance must never read as a receipt
	pe.flags.ignore_permissions = True
	pe.set_missing_values()
	pe.insert()
	pe.submit()
	return {"payment_entry": pe.name}


# --------------------------------------------------------------------------- #
# Adjust a customer advance against an invoice (ERPNext-native)
#   Draft     → the Sales Invoice `advances` child table (reconciles on submit).
#   Submitted → Payment Reconciliation (link) / Unreconcile Payment (unlink).
# --------------------------------------------------------------------------- #
def _receivable_for(customer, company):
	from erpnext.accounts.party import get_party_account

	return get_party_account("Customer", customer, company)


def _draft_committed(pe_names):
	"""How much of each Payment Entry is already earmarked on DRAFT invoices' advances tables.
	A draft advance does not reduce the Payment Entry's `unallocated_amount` (nothing hits the
	ledger until submit), so we net it off ourselves — otherwise an advance already adjusted on
	a draft keeps showing as fully available and can be linked again and again."""
	if not pe_names:
		return {}
	rows = frappe.get_all(
		"Sales Invoice Advance",
		filters={"reference_type": PE, "reference_name": ["in", list(pe_names)], "docstatus": 0},
		fields=["reference_name", "allocated_amount"],
	)
	out = {}
	for r in rows:
		out[r.reference_name] = out.get(r.reference_name, 0) + flt(r.allocated_amount)
	return out


@frappe.whitelist()
def available_advances(name: str):
	"""The invoice customer's on-account advances that can still be adjusted against this
	invoice, oldest first — the Payment Entry's unallocated balance net of anything already
	earmarked on any draft invoice (including this one)."""
	si = frappe.get_doc(SI, name)
	si.check_permission("read")
	rows = frappe.get_all(
		PE,
		filters={
			"docstatus": 1,
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": si.customer,
			"company": si.company,
			"unallocated_amount": [">", 0.01],
		},
		fields=["name", "posting_date", "unallocated_amount", "mode_of_payment", "reference_no", "paid_to"],
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
				"deposit_to": r.paid_to,
			}
		)
	return out


def _reconcile_advance(si, pe, amount):
	"""Allocate `amount` of an unallocated advance Payment Entry against a submitted invoice via
	the native Payment Reconciliation tool (honours a partial allocation)."""
	pr = frappe.new_doc("Payment Reconciliation")
	pr.company = si.company
	pr.party_type = "Customer"
	pr.party = si.customer
	pr.receivable_payable_account = _receivable_for(si.customer, si.company)
	pr.get_unreconciled_entries()
	inv_d = [i.as_dict() for i in pr.invoices if i.invoice_number == si.name]
	pay_d = [p.as_dict() for p in pr.payments if p.reference_name == pe.name]
	if not inv_d or not pay_d:
		frappe.throw(_("Could not find the advance or the invoice among unreconciled entries."))
	pr.allocate_entries({"invoices": inv_d, "payments": pay_d})
	# allocate_entries auto-fills full amounts; trim to the requested partial while leaving
	# unreconciled_amount untouched (the modified-check validates it against the ledger).
	matched = False
	for a in pr.allocation:
		if a.reference_name == pe.name and a.invoice_number == si.name:
			a.allocated_amount = amount
			matched = True
		else:
			a.allocated_amount = 0
	pr.set("allocation", [a for a in pr.allocation if flt(a.allocated_amount) > 0])
	if not matched or not pr.allocation:
		frappe.throw(_("Allocation could not be prepared."))
	pr.reconcile()


@frappe.whitelist()
def link_advance(name: str, payment_entry: str, amount: float | int | str):
	"""Adjust `amount` of a customer advance against this invoice, reducing its outstanding."""
	si = frappe.get_doc(SI, name)
	si.check_permission("write")
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter an allocation greater than zero."))

	pe = frappe.get_doc(PE, payment_entry)
	if pe.docstatus != 1 or pe.payment_type != "Receive" or pe.party != si.customer:
		frappe.throw(_("{0} is not an advance from this customer.").format(payment_entry))
	# On-account advance being adjusted — flag it durably so it always reads as an advance
	# (not a receipt), even once fully consumed, and to backfill entries made before this flag.
	if not pe.get("custom_is_bs_advance"):
		frappe.db.set_value(PE, payment_entry, "custom_is_bs_advance", 1, update_modified=False)
	available = flt(pe.unallocated_amount)
	if amount > available + 0.01:
		frappe.throw(_("Only {0} is unadjusted on {1}.").format(available, payment_entry))

	if si.docstatus == 0:
		existing = next(
			(a for a in si.advances if a.reference_type == PE and a.reference_name == payment_entry), None
		)
		prior = flt(existing.allocated_amount) if existing else 0
		other_rows = sum(flt(a.allocated_amount) for a in si.advances if a is not existing)
		# The advance can back at most its own unadjusted balance (net of what it already backs
		# on OTHER drafts), and never more than the invoice's own total.
		committed_elsewhere = flt(_draft_committed([payment_entry]).get(payment_entry, 0)) - prior
		pe_room = available - committed_elsewhere - prior
		invoice_room = flt(si.grand_total) - other_rows - prior
		room = min(pe_room, invoice_room)
		if room <= 0.01:
			frappe.throw(_("This advance is already fully adjusted against the invoice."))
		if amount > room + 0.01:
			frappe.throw(
				_("At most {0} more of {1} can be adjusted against this invoice.").format(room, payment_entry)
			)
		if existing:
			existing.advance_amount = available
			existing.allocated_amount = prior + amount
		else:
			si.append(
				"advances",
				{
					"reference_type": PE,
					"reference_name": payment_entry,
					"advance_amount": available,
					"allocated_amount": amount,
					"remarks": pe.remarks,
				},
			)
		si.flags.ignore_permissions = True
		si.save()
	elif si.docstatus == 1:
		if flt(si.outstanding_amount) <= 0.01:
			frappe.throw(_("This invoice is already settled."))
		_reconcile_advance(si, pe, min(amount, flt(si.outstanding_amount)))
	else:
		frappe.throw(_("A cancelled invoice cannot take advances."))
	return {"payment": _payment_summary(name)}


@frappe.whitelist()
def unlink_advance(name: str, payment_entry: str):
	"""Reverse an advance adjustment — remove the draft `advances` row, or unreconcile the
	Payment Entry from a submitted invoice (native Unreconcile Payment)."""
	si = frappe.get_doc(SI, name)
	si.check_permission("write")
	if si.docstatus == 0:
		si.set(
			"advances",
			[a for a in si.advances if not (a.reference_type == PE and a.reference_name == payment_entry)],
		)
		si.flags.ignore_permissions = True
		si.save()
	elif si.docstatus == 1:
		from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import (
			create_unreconcile_doc_for_selection,
		)

		create_unreconcile_doc_for_selection(
			frappe.as_json(
				[
					{
						"company": si.company,
						"voucher_type": PE,
						"voucher_no": payment_entry,
						"against_voucher_type": SI,
						"against_voucher_no": si.name,
					}
				]
			)
		)
	else:
		frappe.throw(_("Nothing to unlink on a cancelled invoice."))
	return {"payment": _payment_summary(name)}


@frappe.whitelist()
def receivables_summary(company: str | None = None):
	"""Header totals for the Invoices panel — total outstanding receivable (submitted, unpaid
	Sales Invoices) and total unallocated customer advances — for the active company."""
	company = company or default_company()
	outstanding = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(outstanding_amount), 0)
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND company = %(company)s AND outstanding_amount > 0
		""",
		{"company": company},
	)
	return {
		"outstanding": flt(outstanding[0][0]) if outstanding else 0,
		"advances": advances_summary(company)["total"],
	}


@frappe.whitelist()
def advances_summary(company: str | None = None):
	"""Total unallocated customer advances held for the active (default) company."""
	company = company or default_company()
	total = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(unallocated_amount), 0)
		FROM `tabPayment Entry`
		WHERE docstatus = 1 AND payment_type = 'Receive' AND party_type = 'Customer'
			AND company = %(company)s AND unallocated_amount > 0
		""",
		{"company": company},
	)
	return {"total": flt(total[0][0]) if total else 0}


# --------------------------------------------------------------------------- #
# Pickers
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def list_deposit_accounts(company: str | None = None):
	"""Bank/Cash accounts a receipt can be deposited INTO — the active (default) company."""
	company = company or default_company()
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_type"],
		order_by="account_type, name",
	)


@frappe.whitelist()
def list_tax_templates(company: str | None = None):
	"""Sales Taxes and Charges Templates for the picker (GST/VAT/none — whatever is seeded)."""
	filters = {"disabled": 0}
	if company:
		filters["company"] = company
	# is_default first so a new invoice can pre-select the company's default template
	# (mirrors the prototype starting each invoice with its default tax pre-filled).
	return frappe.get_all(
		"Sales Taxes and Charges Template",
		filters=filters,
		fields=["name", "title", "is_default"],
		order_by="is_default desc, title asc",
	)


@frappe.whitelist()
def get_tax_template_rows(template: str):
	"""Resolve a Sales tax template's rows into the invoice's tax-table shape (Bill pattern)."""
	doc = frappe.get_doc("Sales Taxes and Charges Template", template)
	return [
		{
			"charge_type": t.charge_type,
			"account_head": t.account_head,
			"description": t.description or t.account_head,
			"rate": t.rate,
		}
		for t in doc.taxes
	]


def _html_to_text(html):
	"""Render a Terms & Conditions body (a Text Editor / HTML field) as friendly plain text
	for the invoice's terms box — block tags become line breaks, remaining tags are stripped.
	Plain text (no markup) is returned unchanged."""
	if not html or "<" not in html:
		return html or ""
	import html as _html
	import re

	text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\n", html, flags=re.I)
	text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
	text = re.sub(r"<li[^>]*>", "• ", text, flags=re.I)
	text = re.sub(r"<[^>]+>", "", text)
	return re.sub(r"\n{3,}", "\n\n", _html.unescape(text)).strip()


@frappe.whitelist()
def get_terms(name: str):
	"""The body of a Terms and Conditions template as plain text (imported into the invoice
	terms box). ERPNext stores it as HTML, which is unfriendly to edit — so convert it."""
	return {"terms": _html_to_text(frappe.db.get_value("Terms and Conditions", name, "terms"))}


@frappe.whitelist()
def list_payment_modes():
	return frappe.get_all("Mode of Payment", fields=["name"], order_by="name", pluck="name")
