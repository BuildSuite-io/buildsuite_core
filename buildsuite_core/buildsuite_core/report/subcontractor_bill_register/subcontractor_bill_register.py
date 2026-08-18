# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Subcontractor Bill Register — every subcontractor bill across projects, with gross, retention
and net payable. A Script Report so its conditions bind only when a filter is set (Frappe runs
with empty filters on page load). All filters are optional — the register spans projects."""

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": "Bill",
			"fieldname": "bill",
			"fieldtype": "Link",
			"options": "Subcontractor Bill",
			"width": 160,
		},
		{
			"label": "Subcontractor",
			"fieldname": "subcontractor",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180,
		},
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
		{"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": "Gross", "fieldname": "gross", "fieldtype": "Currency", "width": 120},
		{"label": "Retention", "fieldname": "retention", "fieldtype": "Currency", "width": 120},
		{"label": "Net Payable", "fieldname": "net_payable", "fieldtype": "Currency", "width": 130},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
	]

	conditions = ""
	if filters.get("subcontractor"):
		conditions += " AND sb.subcontractor = %(subcontractor)s"
	if filters.get("project"):
		conditions += " AND sb.project = %(project)s"
	if filters.get("status"):
		conditions += " AND sb.status = %(status)s"
	if filters.get("from_date"):
		conditions += " AND sb.date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND sb.date <= %(to_date)s"

	data = frappe.db.sql(
		f"""
		SELECT sb.name AS bill, sb.subcontractor, sb.project, sb.date,
			sb.gross, sb.retention_amount AS retention, sb.net_payable, sb.status
		FROM `tabSubcontractor Bill` sb
		WHERE sb.docstatus < 2 {conditions}
		ORDER BY sb.date DESC, sb.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
