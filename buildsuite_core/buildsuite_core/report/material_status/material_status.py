# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Material Status — ordered → received → consumed → at site, per item, for one project,
with a delivery Flag (overdue / pending) and Late-deliveries / Not-fully-delivered filters.

A Script Report (not a Query Report) so the SQL is built with the project condition ONLY when
a project is set: Frappe fires an initial run with empty filters on page load, and a Query
Report's `%(project)s` substitution would blow up on that. Project is required (the report is
project-scoped), so with none set we simply return no rows."""

import frappe
from frappe import _
from frappe.utils import flt


def _qty(v):
	"""Quantity as a grouped string — whole numbers without decimals (matches the prototype)."""
	v = flt(v)
	return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 220},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 80},
		{"label": _("Ordered"), "fieldname": "ordered", "fieldtype": "Float", "width": 100},
		{"label": _("Received"), "fieldname": "received", "fieldtype": "Float", "width": 100},
		{"label": _("Consumed"), "fieldname": "consumed", "fieldtype": "Float", "width": 100},
		{"label": _("At Site"), "fieldname": "at_site", "fieldtype": "Float", "width": 100},
		{"label": _("Flag"), "fieldname": "flag", "fieldtype": "Data", "width": 180},
	]
	if not filters.get("project"):
		return columns, []

	# Late deliveries only / Not fully delivered — applied on the aggregated item.
	having_extra = ""
	if filters.get("late_only"):
		having_extra += " AND MAX(overdue_days) > 0"
	if filters.get("not_fully_delivered"):
		having_extra += " AND SUM(ordered) - SUM(received) > 0"

	data = frappe.db.sql(
		"""
		SELECT item_code, MAX(uom) AS uom,
			SUM(ordered) AS ordered, SUM(received) AS received, SUM(consumed) AS consumed,
			SUM(received) - SUM(consumed) AS at_site,
			MAX(overdue_days) AS overdue_days
		FROM (
			SELECT poi.item_code, poi.uom AS uom, poi.qty AS ordered, 0 received, 0 consumed,
				CASE WHEN poi.schedule_date < CURDATE() AND po.per_received < 100
					THEN DATEDIFF(CURDATE(), poi.schedule_date) ELSE 0 END AS overdue_days
				FROM `tabPurchase Order Item` poi JOIN `tabPurchase Order` po ON po.name = poi.parent
				WHERE po.docstatus = 1 AND poi.project = %(project)s
			UNION ALL
			SELECT pri.item_code, pri.uom, 0, pri.received_qty, 0, 0
				FROM `tabPurchase Receipt Item` pri JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
				WHERE pr.docstatus = 1 AND pri.project = %(project)s
			UNION ALL
			SELECT sed.item_code, sed.uom, 0, 0, sed.qty, 0
				FROM `tabStock Entry Detail` sed JOIN `tabStock Entry` se ON se.name = sed.parent
				WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Issue'
					AND se.project = %(project)s
		) x
		GROUP BY item_code
		HAVING SUM(ordered) + SUM(received) + SUM(consumed) > 0 """ + having_extra + """
		ORDER BY item_code
		""",
		filters,
		as_dict=True,
	)

	# Delivery Flag: overdue beats pending (mirrors the prototype badge).
	for row in data:
		overdue = int(row.overdue_days or 0)
		pending = flt(row.ordered) - flt(row.received)
		if overdue > 0:
			row["flag"] = f"Delivery overdue {overdue}d"
		elif pending > 0:
			row["flag"] = f"{_qty(pending)} pending"
		else:
			row["flag"] = "—"

	return columns, data
