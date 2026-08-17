# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Billing and Collection — invoiced, received, overdue and retention held for one project.

A Script Report so the filters bind only when present (Frappe runs with empty filters on
page load; a Query Report's %(x)s would crash). Project is required; the date range is
optional and applied only when supplied."""

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
		{"label": "Invoiced", "fieldname": "invoiced", "fieldtype": "Currency", "width": 120},
		{"label": "Received", "fieldname": "received", "fieldtype": "Currency", "width": 120},
		{"label": "Outstanding", "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
		{"label": "Overdue", "fieldname": "overdue", "fieldtype": "Currency", "width": 120},
		{"label": "Retention Held", "fieldname": "retention_held", "fieldtype": "Currency", "width": 130},
	]
	if not filters.get("project"):
		return columns, []

	conditions = ""
	if filters.get("from_date"):
		conditions += " AND si.posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND si.posting_date <= %(to_date)s"

	data = frappe.db.sql(
		f"""
		SELECT si.project AS project,
			SUM(si.grand_total) AS invoiced,
			SUM(si.grand_total - si.outstanding_amount) AS received,
			SUM(si.outstanding_amount) AS outstanding,
			SUM(CASE WHEN si.due_date < CURDATE() THEN si.outstanding_amount ELSE 0 END) AS overdue,
			(SELECT IFNULL(SUM(sb.retention_amount), 0) FROM `tabSubcontractor Bill` sb
				WHERE sb.docstatus = 1 AND sb.project = si.project) AS retention_held
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 AND si.project = %(project)s {conditions}
		GROUP BY si.project ORDER BY SUM(si.outstanding_amount) DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
