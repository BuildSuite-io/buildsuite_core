# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Subcontractor Ledger — one row per subcontractor: value committed on work orders, billed net,
retention held, and the balance still to bill. A Script Report; the project filter is optional
(the ledger spans projects). Only submitted work orders and bills count."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Subcontractor"), "fieldname": "subcontractor", "fieldtype": "Link", "options": "Supplier", "width": 220},
		{"label": _("Committed"), "fieldname": "committed", "fieldtype": "Currency", "width": 130},
		{"label": _("Billed (net)"), "fieldname": "billed", "fieldtype": "Currency", "width": 130},
		{"label": _("Retention Held"), "fieldname": "retention", "fieldtype": "Currency", "width": 140},
		{"label": _("To Bill"), "fieldname": "to_bill", "fieldtype": "Currency", "width": 130},
	]

	proj = " AND project = %(project)s" if filters.get("project") else ""

	committed = {
		r.subcontractor: r.total
		for r in frappe.db.sql(
			"SELECT subcontractor, SUM(total_value) AS total FROM `tabSubcontractor Work Order` "
			"WHERE docstatus = 1" + proj + " GROUP BY subcontractor",
			filters,
			as_dict=True,
		)
	}
	bills = frappe.db.sql(
		"SELECT subcontractor, SUM(net_payable) AS net, SUM(retention_amount) AS retention "
		"FROM `tabSubcontractor Bill` WHERE docstatus = 1" + proj + " GROUP BY subcontractor",
		filters,
		as_dict=True,
	)
	billed = {r.subcontractor: r.net for r in bills}
	retention = {r.subcontractor: r.retention for r in bills}

	data = []
	for sub in sorted(set(committed) | set(billed)):
		c = committed.get(sub) or 0
		b = billed.get(sub) or 0
		data.append({
			"subcontractor": sub,
			"committed": c,
			"billed": b,
			"retention": retention.get(sub) or 0,
			"to_bill": c - b,
		})
	return columns, data
