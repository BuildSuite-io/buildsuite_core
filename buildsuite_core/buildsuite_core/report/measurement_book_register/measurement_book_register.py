# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Measurement Book Register — every measurement book across projects, with the work order (and its
subcontractor), entry count and measured total. A Script Report so its conditions bind only when a
filter is set (Frappe runs with empty filters on page load). All filters are optional."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": _("MB"),
			"fieldname": "measurement_book",
			"fieldtype": "Link",
			"options": "Measurement Book",
			"width": 160,
		},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 180},
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Subcontractor Work Order",
			"width": 150,
		},
		# The WO's subcontractor, shown alongside the work order (prototype pairs them).
		{"label": _("Subcontractor"), "fieldname": "subcontractor", "fieldtype": "Data", "width": 180},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Entries"), "fieldname": "entries", "fieldtype": "Int", "width": 90},
		{"label": _("Measured"), "fieldname": "measured", "fieldtype": "Float", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
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
		"""
		SELECT mb.name AS measurement_book, prj.project_name AS project, mb.work_order,
			sup.supplier_name AS subcontractor, mb.date,
			(SELECT COUNT(*) FROM `tabMeasurement Book Entry` e WHERE e.parent = mb.name) AS entries,
			mb.measured_total AS measured, mb.status
		FROM `tabMeasurement Book` mb
		LEFT JOIN `tabProject` prj ON prj.name = mb.project
		LEFT JOIN `tabSubcontractor Work Order` wo ON wo.name = mb.work_order
		LEFT JOIN `tabSupplier` sup ON sup.name = wo.subcontractor
		-- Measurement Book is NOT submittable (its lifecycle is the `status` field: Draft →
		-- Certified), so it stays at docstatus 0. Show non-cancelled books but EXCLUDE drafts —
		-- only certified measurements belong in the register.
		WHERE mb.docstatus < 2 AND mb.status != 'Draft' """ + conditions + """
		ORDER BY mb.date DESC, mb.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
