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


def _serialize(doc):
	return {
		"name": doc.name,
		"customer": doc.customer,
		"customer_name": doc.customer_name,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"company": doc.company,
		"date": str(doc.posting_date) if doc.posting_date else None,
		"due_date": str(doc.due_date) if doc.due_date else None,
		"taxes_and_charges": doc.taxes_and_charges,
		"docstatus": doc.docstatus,
		"net_total": doc.net_total,
		"total_taxes_and_charges": doc.total_taxes_and_charges,
		"grand_total": doc.grand_total,
		"items": [
			{"description": r.description, "qty": r.qty, "rate": r.rate, "amount": r.amount}
			for r in doc.items
		],
		"taxes": [
			{"description": t.description, "rate": t.rate, "tax_amount": t.tax_amount, "account_head": t.account_head}
			for t in doc.taxes
		],
		"payment": _payment_summary(doc.name),
	}


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def list_invoices(project=None, company=None):
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
			"name", "customer", "customer_name", "project", "posting_date", "due_date",
			"grand_total", "outstanding_amount", "status", "docstatus",
		],
		order_by="posting_date desc, creation desc",
		limit_page_length=0,
	)
	pids = list({r.project for r in rows if r.project})
	pnames = (
		{p.name: p.project_name for p in frappe.get_all("Project", filters={"name": ["in", pids]}, fields=["name", "project_name"])}
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
def get_invoice(name):
	doc = frappe.get_doc(SI, name)
	doc.check_permission("read")
	return _serialize(doc)


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def save_invoice(payload):
	"""Create or edit a DRAFT Sales Invoice. payload: {name?, customer, project?, date,
	due_date?, taxes_and_charges?, items:[{description, qty, rate}]}."""
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

	template = data.get("taxes_and_charges")
	if template:
		si.taxes_and_charges = template
		for t in frappe.get_doc("Sales Taxes and Charges Template", template).taxes:
			si.append(
				"taxes",
				{
					"charge_type": t.charge_type or "On Net Total",
					"account_head": t.account_head,
					"description": t.description or t.account_head,
					"rate": flt(t.rate),
				},
			)

	si.flags.ignore_permissions = True
	si.set_missing_values()
	si.save()
	return {"name": si.name}


@frappe.whitelist()
def submit_invoice(name):
	si = frappe.get_doc(SI, name)
	si.check_permission("submit")
	si.flags.ignore_permissions = True
	si.submit()
	return {"name": si.name, "payment": _payment_summary(name)}


@frappe.whitelist()
def cancel_invoice(name):
	si = frappe.get_doc(SI, name)
	si.check_permission("cancel")
	si.flags.ignore_permissions = True
	si.cancel()
	return {"name": name, "cancelled": True}


@frappe.whitelist()
def delete_invoice(name):
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
def record_receipt(name, amount=None, date=None, mode_of_payment=None, deposit_to=None, reference_no=None):
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
def list_receipts(name):
	"""Payment Entries allocated to this invoice."""
	refs = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": SI, "reference_name": name, "docstatus": 1},
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


# --------------------------------------------------------------------------- #
# Pickers
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def list_deposit_accounts(company=None):
	"""Bank/Cash accounts a receipt can be deposited INTO — the active (default) company."""
	company = company or default_company()
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_type"],
		order_by="account_type, name",
	)


@frappe.whitelist()
def list_tax_templates(company=None):
	"""Sales Taxes and Charges Templates for the picker (GST/VAT/none — whatever is seeded)."""
	filters = {"disabled": 0}
	if company:
		filters["company"] = company
	return frappe.get_all(
		"Sales Taxes and Charges Template", filters=filters, fields=["name", "title"], order_by="title asc"
	)


@frappe.whitelist()
def list_payment_modes():
	return frappe.get_all("Mode of Payment", fields=["name"], order_by="name", pluck="name")
