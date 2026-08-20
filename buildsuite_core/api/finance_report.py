# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Real-data backends for the two bespoke Project Finance report views (Receivables & Payables
aged, Financial Position). These mirror what the prototype's mock store returned, so the Vue
views render the prototype layout against live data. Finance is single-company for now, so both
default to the site's default company."""

import frappe
from frappe.utils import flt

from buildsuite_core.utils.project import default_company

BUCKETS = ["Current", "0-30", "31-60", "61-90", "90+"]


def _bucket(days):
	days = int(days or 0)
	if days <= 0:
		return "Current"
	if days <= 30:
		return "0-30"
	if days <= 60:
		return "31-60"
	if days <= 90:
		return "61-90"
	return "90+"


@frappe.whitelist()
def receivables_and_payables(company=None):
	"""Aged open receivables (Sales Invoices) and payables (Purchase Invoices), each row bucketed
	by days overdue. Payables carry a supplier/subcontractor kind + any retention withheld."""
	company = company or default_company()
	receivables = frappe.db.sql(
		"""SELECT name AS id, customer_name AS party, due_date AS due,
			outstanding_amount AS outstanding, GREATEST(DATEDIFF(CURDATE(), due_date), 0) AS days_overdue
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND outstanding_amount > 0 AND company = %s
		ORDER BY due_date""",
		(company,),
		as_dict=True,
	)
	payables = frappe.db.sql(
		"""SELECT pi.name AS id, pi.supplier_name AS party, pi.due_date AS due,
			pi.outstanding_amount AS outstanding, GREATEST(DATEDIFF(CURDATE(), pi.due_date), 0) AS days_overdue,
			IFNULL((SELECT SUM(sb.retention_amount) FROM `tabSubcontractor Bill` sb
				WHERE sb.purchase_invoice = pi.name AND sb.docstatus = 1), 0) AS retention,
			(SELECT s.supplier_group FROM `tabSupplier` s WHERE s.name = pi.supplier) AS supplier_group
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0 AND pi.company = %s
		ORDER BY pi.due_date""",
		(company,),
		as_dict=True,
	)
	for r in receivables:
		r["bucket"] = _bucket(r["days_overdue"])
		r["due"] = str(r["due"]) if r.get("due") else None
	for r in payables:
		r["bucket"] = _bucket(r["days_overdue"])
		r["due"] = str(r["due"]) if r.get("due") else None
		r["kind"] = "subcontractor" if (r.get("supplier_group") == "Subcontractor") else "supplier"
		r.pop("supplier_group", None)
	return {"receivables": receivables, "payables": payables, "buckets": BUCKETS}


def _account_names(company, account_type, contains=None, excludes=None):
	names = frappe.get_all(
		"Account", filters={"company": company, "account_type": account_type, "is_group": 0}, pluck="name"
	)
	if contains:
		names = [n for n in names if contains in n]
	if excludes:
		names = [n for n in names if not any(x in n for x in excludes)]
	return names


def _gl_balance(company, accounts):
	if not accounts:
		return 0.0
	return flt(
		frappe.db.sql(
			"""SELECT IFNULL(SUM(debit - credit), 0) FROM `tabGL Entry`
			WHERE is_cancelled = 0 AND company = %s AND account IN %s""",
			(company, tuple(accounts)),
		)[0][0]
	)


@frappe.whitelist()
def financial_position(company=None):
	"""What we have (bank, cash, petty cash out with holders, customers owe) vs what we owe
	(suppliers, subcontractors, retention held), and the net. Balances from the GL and open
	documents. Supplier/customer advances and own-pocket reimbursements aren't broken out yet."""
	company = company or default_company()

	def doc_sum(doctype, field):
		return flt(
			frappe.db.sql(
				f"SELECT IFNULL(SUM(`{field}`), 0) FROM `tab{doctype}` WHERE docstatus = 1 AND company = %s",
				(company,),
			)[0][0]
		)

	bank = _gl_balance(company, _account_names(company, "Bank"))
	cash = _gl_balance(company, _account_names(company, "Cash", excludes=["Petty"]))
	petty = _gl_balance(company, _account_names(company, "Cash", contains="Petty"))
	customers_owe = doc_sum("Sales Invoice", "outstanding_amount")
	retention = doc_sum("Subcontractor Bill", "retention_amount")

	# Split open payables into supplier vs subcontractor by the supplier's group.
	pay_rows = frappe.db.sql(
		"""SELECT pi.outstanding_amount AS amt,
			(SELECT s.supplier_group FROM `tabSupplier` s WHERE s.name = pi.supplier) AS grp
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1 AND pi.company = %s AND pi.outstanding_amount > 0""",
		(company,),
		as_dict=True,
	)
	subcontractors = flt(sum(r.amt for r in pay_rows if r.grp == "Subcontractor"))
	suppliers = flt(sum(r.amt for r in pay_rows if r.grp != "Subcontractor"))

	have = {
		"bank": bank,
		"cash": cash,
		"pettyCashOut": petty,
		"customersOwe": customers_owe,
		"advancesPaid": 0,
	}
	owe = {
		"suppliers": suppliers,
		"subcontractors": subcontractors,
		"retention": retention,
		"advancesReceived": 0,
		"toReimburse": 0,
	}
	return {"have": have, "owe": owe, "net": sum(have.values()) - sum(owe.values())}
