# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Work Order Register — every subcontractor work order across projects, with committed value
and % billed to date. A Script Report so its conditions bind only when a filter is set (Frappe
runs with empty filters on page load). All filters are optional — the register spans projects."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": _("WO"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Subcontractor Work Order",
			"width": 160,
		},
		# Subcontractor / Project show the NAME (plain text) — only the WO is a link, per the
		# prototype registers.
		{"label": _("Subcontractor"), "fieldname": "subcontractor", "fieldtype": "Data", "width": 180},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 180},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Type"), "fieldname": "delivery_type", "fieldtype": "Data", "width": 110},
		{"label": _("Value"), "fieldname": "total_value", "fieldtype": "Currency", "width": 130},
		{"label": _("% Billed"), "fieldname": "percent_billed", "fieldtype": "Percent", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]

	conditions = ""
	if filters.get("subcontractor"):
		conditions += " AND wo.subcontractor = %(subcontractor)s"
	if filters.get("project"):
		conditions += " AND wo.project = %(project)s"
	if filters.get("status"):
		conditions += " AND wo.status = %(status)s"
	if filters.get("from_date"):
		conditions += " AND wo.date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND wo.date <= %(to_date)s"

	data = frappe.db.sql(
		"""
		SELECT wo.name AS work_order, sup.supplier_name AS subcontractor,
			prj.project_name AS project, wo.date, wo.delivery_type, wo.total_value, wo.status,
			LEAST(100, ROUND(IFNULL(
				(SELECT SUM(sb.gross) FROM `tabSubcontractor Bill` sb
					WHERE sb.work_order = wo.name AND sb.docstatus = 1), 0)
				/ NULLIF(wo.total_value, 0) * 100, 1)) AS percent_billed
		FROM `tabSubcontractor Work Order` wo
		LEFT JOIN `tabSupplier` sup ON sup.name = wo.subcontractor
		LEFT JOIN `tabProject` prj ON prj.name = wo.project
		-- Exclude drafts. The WO is submittable, but its `status` can still read Draft at
		-- docstatus 1 (the workflow state lags docstatus) — the register should list only
		-- progressed work orders, not draft ones.
		WHERE wo.docstatus = 1 AND wo.status != 'Draft' """ + conditions + """
		ORDER BY wo.date DESC, wo.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
