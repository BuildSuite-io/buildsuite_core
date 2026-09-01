# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Billing and Collection — one row per client invoice on a project (raised, received,
outstanding, days overdue), with Invoiced / Received / Overdue / Retention held summary
cards. Matches the prototype's per-invoice view rather than a single cumulative total.

A Script Report so the filters bind only when present (Frappe runs with empty filters on
page load; a Query Report's %(x)s would crash). Project is required; the date range is
optional and applied only when supplied.

Retention withheld by the client isn't modelled on the invoice yet — the retention_amount
field exists only on subcontractor bills (what we withhold from subcontractors, a different
figure). Reported as "—" rather than a zero that would read as "the client withholds nothing"."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"label": _("Invoice"),
			"fieldname": "invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{"label": _("Raised"), "fieldname": "raised", "fieldtype": "Date", "width": 100},
		{"label": _("Due"), "fieldname": "due_date", "fieldtype": "Date", "width": 100},
		{"label": _("Overdue (days)"), "fieldname": "overdue_days", "fieldtype": "Int", "width": 110},
		{"label": _("Invoiced"), "fieldname": "invoiced", "fieldtype": "Currency", "width": 120},
		{"label": _("Received"), "fieldname": "received", "fieldtype": "Currency", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
		{"label": _("Retention"), "fieldname": "retention", "fieldtype": "Data", "width": 90},
	]
	if not filters.get("project"):
		return columns, [], None, None, []

	conditions = ""
	if filters.get("from_date"):
		conditions += " AND si.posting_date >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " AND si.posting_date <= %(to_date)s"
	if filters.get("overdue_only"):
		conditions += " AND si.outstanding_amount > 0 AND si.due_date < CURDATE()"

	data = frappe.db.sql(
		"""
		SELECT si.name AS invoice,
			si.customer AS customer,
			si.posting_date AS raised,
			si.due_date AS due_date,
			CASE WHEN si.outstanding_amount > 0 AND si.due_date < CURDATE()
				THEN DATEDIFF(CURDATE(), si.due_date) ELSE 0 END AS overdue_days,
			si.grand_total AS invoiced,
			si.grand_total - si.outstanding_amount AS received,
			si.outstanding_amount AS outstanding
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 AND si.project = %(project)s """ + conditions + """
		ORDER BY si.posting_date DESC, si.name DESC
		""",
		filters,
		as_dict=True,
	)

	# Client retention isn't modelled on the invoice — show "—" per row (see module docstring).
	for row in data:
		row["retention"] = "—"

	invoiced = sum(row.invoiced or 0 for row in data)
	received = sum(row.received or 0 for row in data)
	overdue = sum(row.outstanding or 0 for row in data if row.overdue_days)

	report_summary = [
		{"label": _("Invoiced"), "value": invoiced, "datatype": "Currency"},
		{"label": _("Received"), "value": received, "datatype": "Currency", "indicator": "green"},
		{"label": _("Overdue"), "value": overdue, "datatype": "Currency", "indicator": "red" if overdue else ""},
		{"label": _("Retention held"), "value": "—", "datatype": "Data"},
	]

	return columns, data, None, None, report_summary
