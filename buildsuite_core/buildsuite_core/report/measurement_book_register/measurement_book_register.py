# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Measurement Book Register — every measurement book across projects, with entry count and
measured total. A Script Report so its conditions bind only when a filter is set (Frappe runs
with empty filters on page load). All filters are optional — the register spans projects."""

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": "MB",
			"fieldname": "measurement_book",
			"fieldtype": "Link",
			"options": "Measurement Book",
			"width": 160,
		},
		{"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
		{
			"label": "Work Order",
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Subcontractor Work Order",
			"width": 160,
		},
		{"label": "Date", "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": "Entries", "fieldname": "entries", "fieldtype": "Int", "width": 90},
		{"label": "Measured", "fieldname": "measured", "fieldtype": "Float", "width": 120},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 110},
	]

	conditions = ""
	if filters.get("work_order"):
		conditions += " AND mb.work_order = %(work_order)s"
	if filters.get("project"):
		conditions += " AND mb.project = %(project)s"
	if filters.get("status"):
		conditions += " AND mb.status = %(status)s"
	if filters.get("from_date"):
		conditions += " AND mb.date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND mb.date <= %(to_date)s"

	data = frappe.db.sql(
		f"""
		SELECT mb.name AS measurement_book, mb.project, mb.work_order, mb.date,
			(SELECT COUNT(*) FROM `tabMeasurement Book Entry` e WHERE e.parent = mb.name) AS entries,
			mb.measured_total AS measured, mb.status
		FROM `tabMeasurement Book` mb
		WHERE mb.docstatus < 2 {conditions}
		ORDER BY mb.date DESC, mb.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
