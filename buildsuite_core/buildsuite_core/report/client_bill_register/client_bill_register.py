# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Client Bill Register — client interim payment certificates (Sales Invoices) per project, with
total claimed and outstanding. A Script Report so conditions bind only when a filter is set; all
filters are optional (the register spans projects)."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 110},
	]
	conditions = ""
	if filters.get("customer"):
		conditions += " AND si.customer = %(customer)s"
	if filters.get("project"):
		conditions += " AND si.project = %(project)s"
	if filters.get("status"):
		conditions += " AND si.status = %(status)s"
	if filters.get("from_date"):
		conditions += " AND si.posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND si.posting_date <= %(to_date)s"
	data = frappe.db.sql(
		"""
		SELECT si.name AS invoice, si.customer, si.project, si.posting_date AS date,
			si.grand_total AS total, si.outstanding_amount AS outstanding, si.status
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 """ + conditions + """
		ORDER BY si.posting_date DESC, si.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
