# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""A submitted Purchase Order line carrying a BOQ cost code is committed spend: it feeds
`po_committed_by_cost_code` and the combined BOQ 'Committed' column
(`subcontract.committed_by_cost_code`), alongside subcontractor work orders. Drafts don't count."""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api import subcontract
from buildsuite_core.api.procurement_docs import po_committed_by_cost_code, save_purchase_order
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPoCommitted(BuildSuiteTestCase):
	def _supplier(self):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"UAT Supplier {self._n}",
				"supplier_group": frappe.db.get_value("Supplier Group", {}, "name"),
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)

	def _item(self):
		return frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"UAT-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
				"item_name": "UAT Stock Item",
				"item_group": frappe.db.get_value("Item Group", {}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert(ignore_permissions=True)

	def _save_po(self, project, supplier, item, qty=2, rate=100, group="A"):
		return save_purchase_order(
			supplier=supplier,
			project=project,
			schedule_date=add_days(nowdate(), 7),
			items=frappe.as_json(
				[
					{
						"item_code": item,
						"qty": qty,
						"rate": rate,
						"cost_code": {
							"type": "group",
							"group_code": group,
							"item_code": None,
							"label": f"{group} · Civil",
						},
					}
				]
			),
		)

	def test_cost_code_round_trips_through_save(self):
		p = self._make_project(company=self.company)
		po = self._save_po(p.name, self._supplier().name, self._item().name, group="A")
		cc = po["items"][0]["cost_code"]
		self.assertIsNotNone(cc)
		self.assertEqual(cc["group_code"], "A")
		self.assertEqual(cc["label"], "A · Civil")

	def test_submitted_po_is_committed_by_cost_code(self):
		p = self._make_project(company=self.company)
		po = self._save_po(p.name, self._supplier().name, self._item().name, qty=2, rate=100, group="A")

		# Draft does not count as committed yet.
		self.assertEqual(po_committed_by_cost_code(p.name).get("A", 0), 0)

		frappe.get_doc("Purchase Order", po["name"]).submit()

		self.assertEqual(po_committed_by_cost_code(p.name).get("A"), 200)
		# The combined BOQ 'Committed' getter folds the PO in.
		self.assertEqual(subcontract.committed_by_cost_code(p.name).get("A"), 200)

	def test_line_without_cost_code_is_ignored(self):
		p = self._make_project(company=self.company)
		po = save_purchase_order(
			supplier=self._supplier().name,
			project=p.name,
			schedule_date=add_days(nowdate(), 7),
			items=frappe.as_json([{"item_code": self._item().name, "qty": 1, "rate": 100}]),
		)
		frappe.get_doc("Purchase Order", po["name"]).submit()
		self.assertEqual(po_committed_by_cost_code(p.name), {})
