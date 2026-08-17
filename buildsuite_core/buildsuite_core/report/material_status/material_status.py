# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Material Status — ordered → received → consumed → at site, per item, for one project.

A Script Report (not a Query Report) so the SQL is built with the project condition ONLY when
a project is set: Frappe fires an initial run with empty filters on page load, and a Query
Report's `%(project)s` substitution would blow up on that. Project is required (the report is
project-scoped), so with none set we simply return no rows."""

import frappe


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 220},
		{"label": "Ordered", "fieldname": "ordered", "fieldtype": "Float", "width": 110},
		{"label": "Received", "fieldname": "received", "fieldtype": "Float", "width": 110},
		{"label": "Consumed", "fieldname": "consumed", "fieldtype": "Float", "width": 110},
		{"label": "At Site", "fieldname": "at_site", "fieldtype": "Float", "width": 110},
	]
	if not filters.get("project"):
		return columns, []

	data = frappe.db.sql(
		"""
		SELECT item_code, SUM(ordered) AS ordered, SUM(received) AS received,
			SUM(consumed) AS consumed, SUM(received) - SUM(consumed) AS at_site
		FROM (
			SELECT poi.item_code, poi.qty AS ordered, 0 received, 0 consumed
				FROM `tabPurchase Order Item` poi JOIN `tabPurchase Order` po ON po.name = poi.parent
				WHERE po.docstatus = 1 AND poi.project = %(project)s
			UNION ALL
			SELECT pri.item_code, 0, pri.received_qty, 0
				FROM `tabPurchase Receipt Item` pri JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
				WHERE pr.docstatus = 1 AND pri.project = %(project)s
			UNION ALL
			SELECT sed.item_code, 0, 0, sed.qty
				FROM `tabStock Entry Detail` sed JOIN `tabStock Entry` se ON se.name = sed.parent
				WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Issue'
					AND se.project = %(project)s
		) x
		GROUP BY item_code HAVING SUM(ordered) + SUM(received) + SUM(consumed) > 0
		ORDER BY item_code
		""",
		filters,
		as_dict=True,
	)
	return columns, data
