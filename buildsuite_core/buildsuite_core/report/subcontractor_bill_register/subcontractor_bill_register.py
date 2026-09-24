# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Subcontractor Bill Register — every subcontractor bill across projects, with gross, retention,
net payable and its payment status (from the linked Purchase Invoice). A Script Report so its
conditions bind only when a filter is set. All filters are optional — the register spans projects."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": _("Bill"),
			"fieldname": "bill",
			"fieldtype": "Link",
			"options": "Subcontractor Bill",
			"width": 160,
		},
		{"label": _("Subcontractor"), "fieldname": "subcontractor", "fieldtype": "Data", "width": 180},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 180},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Gross"), "fieldname": "gross", "fieldtype": "Currency", "width": 120},
		# fieldname "retention" renders amber in the report table.
		{"label": _("Retention"), "fieldname": "retention", "fieldtype": "Currency", "width": 120},
		{"label": _("Net Payable"), "fieldname": "net_payable", "fieldtype": "Currency", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		# Paid/unpaid, from the linked Purchase Invoice — a "_status" fieldname renders as a badge.
		{"label": _("Payment"), "fieldname": "payment_status", "fieldtype": "Data", "width": 110},
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
		"""
		SELECT sb.name AS bill, sup.supplier_name AS subcontractor, prj.project_name AS project,
			sb.date, sb.gross, sb.retention_amount AS retention, sb.net_payable, sb.status,
			COALESCE(pi.status, 'Unpaid') AS payment_status
		FROM `tabSubcontractor Bill` sb
		LEFT JOIN `tabSupplier` sup ON sup.name = sb.subcontractor
		LEFT JOIN `tabProject` prj ON prj.name = sb.project
		LEFT JOIN `tabPurchase Invoice` pi ON pi.name = sb.purchase_invoice
		WHERE sb.docstatus = 1 """ + conditions + """
		ORDER BY sb.date DESC, sb.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
