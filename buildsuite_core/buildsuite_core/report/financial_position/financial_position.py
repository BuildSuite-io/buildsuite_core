# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Financial Position — what we have vs what we owe, right now, for the default company.

A custom Script Report (no single ERPNext report gives this combined "have / owe / net" view).
Balances come from the GL (bank, cash, petty cash) and open documents (customers owe = open
Sales Invoices; suppliers/subcontractors = open Purchase Invoices; retention held = withheld on
submitted Subcontractor Bills). Summary cards give total have, total owe and the net position.

Finance is single-company for now, so this reads the default company. Supplier/customer advances
and own-pocket reimbursements are not yet broken out — they ride inside the payable/receivable
balances until the petty-cash employee dimension work lands."""

import frappe

from buildsuite_core.utils.project import default_company


def _account_names(company, account_type, contains=None, excludes=None):
	names = frappe.get_all(
		"Account",
		filters={"company": company, "account_type": account_type, "is_group": 0},
		pluck="name",
	)
	if contains:
		names = [n for n in names if contains in n]
	if excludes:
		names = [n for n in names if not any(x in n for x in excludes)]
	return names


def _gl_balance(company, accounts):
	if not accounts:
		return 0.0
	return (
		frappe.db.sql(
			"""SELECT IFNULL(SUM(debit - credit), 0) FROM `tabGL Entry`
			WHERE is_cancelled = 0 AND company = %s AND account IN %s""",
			(company, tuple(accounts)),
		)[0][0]
		or 0.0
	)


def _doc_sum(doctype, field, company):
	return (
		frappe.db.sql(
			f"""SELECT IFNULL(SUM(`{field}`), 0) FROM `tab{doctype}`
			WHERE docstatus = 1 AND company = %s""",
			(company,),
		)[0][0]
		or 0.0
	)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	company = filters.get("company") or default_company()

	bank = _gl_balance(company, _account_names(company, "Bank"))
	cash = _gl_balance(company, _account_names(company, "Cash", excludes=["Petty"]))
	petty = _gl_balance(company, _account_names(company, "Cash", contains="Petty"))
	customers_owe = _doc_sum("Sales Invoice", "outstanding_amount", company)
	suppliers_owe = _doc_sum("Purchase Invoice", "outstanding_amount", company)
	retention = _doc_sum("Subcontractor Bill", "retention_amount", company)

	have = [
		("Bank balance", bank),
		("Cash in hand", cash),
		("Petty cash with holders", petty),
		("Customers owe us", customers_owe),
	]
	owe = [
		("Suppliers & subcontractors", suppliers_owe),
		("Retention held", retention),
	]

	columns = [
		{"label": "Item", "fieldname": "item", "fieldtype": "Data", "width": 280},
		{"label": "Side", "fieldname": "side", "fieldtype": "Data", "width": 90},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 160},
	]
	data = [{"item": i, "side": "Have", "amount": v} for i, v in have]
	data += [{"item": i, "side": "Owe", "amount": v} for i, v in owe]

	total_have = sum(v for _, v in have)
	total_owe = sum(v for _, v in owe)
	report_summary = [
		{"label": "Total Have", "value": total_have, "datatype": "Currency", "indicator": "green"},
		{"label": "Total Owe", "value": total_owe, "datatype": "Currency", "indicator": "red"},
		{"label": "Net Position", "value": total_have - total_owe, "datatype": "Currency"},
	]
	return columns, data, None, None, report_summary
