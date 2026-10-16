# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Subcontractor Ledger — one row per subcontractor: value committed on work orders, billed net,
retention held, and the balance still to bill, closed by a bold Total row. A Script Report; the
project filter is optional (the ledger spans projects). Only submitted work orders and bills count."""

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		# The subcontractor is the subject of each row, so link it to the Supplier record (the
		# renderer draws Link columns as a green, clickable link to the subcontractor's page) —
		# the same "link the primary record" rule the WO / Bill / MB registers follow.
		{
			"label": _("Subcontractor"),
			"fieldname": "subcontractor",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 220,
		},
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
	tot = {"committed": 0, "billed": 0, "retention": 0, "to_bill": 0}
	for sub in sorted(set(committed) | set(billed)):
		c = committed.get(sub) or 0
		b = billed.get(sub) or 0
		r = retention.get(sub) or 0
		data.append(
			{
				# The Supplier id (a Link column holds the record name; Suppliers are named by
				# their name here, so this reads as the subcontractor's name and links to it).
				"subcontractor": sub,
				"committed": c,
				"billed": b,
				"retention": r,
				"to_bill": c - b,
			}
		)
		tot["committed"] += c
		tot["billed"] += b
		tot["retention"] += r
		tot["to_bill"] += c - b

	# A bold, ruled Total row so the roll-up reads apart from the per-subcontractor rows
	# (is_total is styled by the report renderer).
	if data:
		data.append(
			{
				"subcontractor": _("Total"),
				"committed": tot["committed"],
				"billed": tot["billed"],
				"retention": tot["retention"],
				"to_bill": tot["to_bill"],
				"is_total": 1,
			}
		)
	# The report emits its OWN bold Total row (is_total) above, so tell Frappe NOT to append its
	# auto-total — otherwise query_report sums every row INCLUDING that Total and shows a second,
	# doubled Total. skip_total_row (the 6th return value) overrides the Report's add_total_row flag,
	# so this holds even before the add_total_row=0 setting syncs to the Report record on migrate.
	skip_total_row = True
	return columns, data, None, None, None, skip_total_row
