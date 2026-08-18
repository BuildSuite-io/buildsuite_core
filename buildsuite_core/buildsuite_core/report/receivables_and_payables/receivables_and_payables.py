# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Receivables and Payables — aged outstanding on both sides in one view: who owes us
(open Sales Invoices) and who we owe (open Purchase Invoices), each aged into buckets.

A custom Script Report because ERPNext's Accounts Receivable and Accounts Payable are two
separate reports; the prototype's Project Finance shows them combined. Company defaults to the
site's default company (finance is single-company for now). Summary cards give the receivable,
payable and net totals."""

import frappe

from buildsuite_core.utils.project import default_company

_BUCKET_ORDER = {"90+": 0, "61-90": 1, "31-60": 2, "1-30": 3, "Current": 4}


def _bucket_sql(col):
	return f"""CASE
		WHEN DATEDIFF(CURDATE(), {col}) <= 0 THEN 'Current'
		WHEN DATEDIFF(CURDATE(), {col}) <= 30 THEN '1-30'
		WHEN DATEDIFF(CURDATE(), {col}) <= 60 THEN '31-60'
		WHEN DATEDIFF(CURDATE(), {col}) <= 90 THEN '61-90'
		ELSE '90+' END"""


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.company = filters.get("company") or default_company()
	side = filters.get("side")

	columns = [
		{"label": "Side", "fieldname": "side", "fieldtype": "Data", "width": 100},
		{"label": "Party", "fieldname": "party", "fieldtype": "Data", "width": 220},
		{"label": "Document", "fieldname": "document", "fieldtype": "Data", "width": 170},
		{"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": "Outstanding", "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
		{"label": "Days Overdue", "fieldname": "days_overdue", "fieldtype": "Int", "width": 110},
		{"label": "Bucket", "fieldname": "bucket", "fieldtype": "Data", "width": 90},
	]

	party_r = " AND si.customer_name LIKE CONCAT('%%', %(party)s, '%%')" if filters.get("party") else ""
	party_p = " AND pi.supplier_name LIKE CONCAT('%%', %(party)s, '%%')" if filters.get("party") else ""

	rows = []
	if side in (None, "", "Receivable"):
		rows += frappe.db.sql(
			f"""
			SELECT 'Receivable' AS side, si.customer_name AS party, si.name AS document,
				si.due_date, si.outstanding_amount AS outstanding,
				GREATEST(DATEDIFF(CURDATE(), si.due_date), 0) AS days_overdue,
				{_bucket_sql("si.due_date")} AS bucket
			FROM `tabSales Invoice` si
			WHERE si.docstatus = 1 AND si.outstanding_amount > 0 AND si.company = %(company)s {party_r}
			""",
			filters,
			as_dict=True,
		)
	if side in (None, "", "Payable"):
		rows += frappe.db.sql(
			f"""
			SELECT 'Payable' AS side, pi.supplier_name AS party, pi.name AS document,
				pi.due_date, pi.outstanding_amount AS outstanding,
				GREATEST(DATEDIFF(CURDATE(), pi.due_date), 0) AS days_overdue,
				{_bucket_sql("pi.due_date")} AS bucket
			FROM `tabPurchase Invoice` pi
			WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0 AND pi.company = %(company)s {party_p}
			""",
			filters,
			as_dict=True,
		)

	if filters.get("bucket"):
		rows = [r for r in rows if r.bucket == filters.bucket]
	rows.sort(key=lambda r: (_BUCKET_ORDER.get(r.bucket, 5), -(r.outstanding or 0)))

	recv = sum(r.outstanding or 0 for r in rows if r.side == "Receivable")
	pay = sum(r.outstanding or 0 for r in rows if r.side == "Payable")
	report_summary = [
		{"label": "Receivable", "value": recv, "datatype": "Currency", "indicator": "green"},
		{"label": "Payable", "value": pay, "datatype": "Currency", "indicator": "red"},
		{"label": "Net", "value": recv - pay, "datatype": "Currency"},
	]
	return columns, rows, None, None, report_summary
