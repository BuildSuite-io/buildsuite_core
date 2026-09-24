# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Client Bill Register — client interim payment certificates (Sales Invoices) per project, with
gross / retention / net claimable, plus document status (draft/submitted) and payment status. A
Script Report so conditions bind only when a filter is set; all filters are optional.

NOTE: client-side RETENTION is not modelled on the Sales Invoice yet (no retention field), so
Retention reads 0 and Net claimable = Gross until a client-retention field is added."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Bill"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
		{"label": _("Client"), "fieldname": "customer", "fieldtype": "Data", "width": 180},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Data", "width": 180},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Gross"), "fieldname": "gross", "fieldtype": "Currency", "width": 120},
		# Client retention is grey (not the amber "retention" fieldname) — no data source yet.
		{"label": _("Retention"), "fieldname": "retention_held", "fieldtype": "Currency", "width": 120},
		{"label": _("Net claimable"), "fieldname": "net_claimable", "fieldtype": "Currency", "width": 130},
		# Doc status (draft/submitted) and payment status both render as badges ("_status" fieldname).
		{"label": _("Doc Status"), "fieldname": "doc_status", "fieldtype": "Data", "width": 110},
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
		SELECT si.name AS invoice, cust.customer_name AS customer, prj.project_name AS project,
			si.posting_date AS date, si.grand_total AS gross, 0 AS retention_held,
			si.grand_total AS net_claimable,
			CASE si.docstatus WHEN 0 THEN 'Draft' WHEN 1 THEN 'Submitted' ELSE 'Cancelled' END AS doc_status,
			si.status
		FROM `tabSales Invoice` si
		LEFT JOIN `tabCustomer` cust ON cust.name = si.customer
		LEFT JOIN `tabProject` prj ON prj.name = si.project
		WHERE si.docstatus < 2 """ + conditions + """
		ORDER BY si.posting_date DESC, si.name DESC
		""",
		filters,
		as_dict=True,
	)
	return columns, data
