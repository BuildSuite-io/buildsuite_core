# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the Procurement workspace KPI dashboard (api/procurement.get_dashboard).

Assertions use before/after DELTAS, not absolute counts — the site may carry
other submitted buying documents outside what a given test creates."""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api import procurement as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestProcurementDashboard(BuildSuiteTestCase):
	def _supplier(self):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"UAT Supplier {self._n}",
				"supplier_group": frappe.db.get_value("Supplier Group", {}, "name"),
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)

	def _item(self, rate_master=None):
		return frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"UAT-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
				"item_name": "UAT Stock Item",
				"item_group": frappe.db.get_value("Item Group", {}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"custom_rate_master": rate_master,
			}
		).insert(ignore_permissions=True)

	def _warehouse(self):
		return frappe.db.get_value("Warehouse", {"is_group": 0, "company": self.company}, "name")

	def _submit_mr(self, project, item, qty=10, rate=50):
		due = add_days(nowdate(), 7)
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": self.company,
				"project": project,
				"schedule_date": due,
				"items": [
					{
						"item_code": item,
						"qty": qty,
						"schedule_date": due,
						"warehouse": self._warehouse(),
						"rate": rate,
					}
				],
			}
		).insert(ignore_permissions=True)
		mr.submit()
		return mr

	def _submit_po(self, project, supplier, item, qty=1, rate=100):
		due = add_days(nowdate(), 7)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier,
				"company": self.company,
				"project": project,
				"schedule_date": due,
				"items": [
					{
						"item_code": item,
						"qty": qty,
						"rate": rate,
						"schedule_date": due,
						"warehouse": self._warehouse(),
					}
				],
			}
		).insert(ignore_permissions=True)
		po.submit()
		return po

	def _submit_pr(self, project, supplier, item, qty=1, rate=100):
		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": self.company,
				"project": project,
				"items": [{"item_code": item, "qty": qty, "rate": rate, "warehouse": self._warehouse()}],
			}
		).insert(ignore_permissions=True)
		pr.submit()
		return pr

	def test_open_mrs_count_endpoint(self):
		# PRC-003 — a submitted, not-yet-fully-ordered MR increments the "Open
		# MRs" KPI, by count and by the still-to-order value.
		p = self._make_project(company=self.company)
		item = self._item()
		before = api.get_dashboard()["open_material_requests"]

		self._submit_mr(p.name, item.name, qty=10, rate=50)  # 500 pending

		after = api.get_dashboard()["open_material_requests"]
		self.assertEqual(after["count"], before["count"] + 1)
		self.assertAlmostEqual(after["value"], before["value"] + 500, places=2)

	def test_on_order_value_endpoint(self):
		# PRC-004 — a submitted, not-yet-fully-received PO increments the
		# "On order" KPI, by count and by its full grand_total.
		p = self._make_project(company=self.company)
		supplier = self._supplier()
		item = self._item()
		before = api.get_dashboard()["on_order"]

		po = self._submit_po(p.name, supplier.name, item.name, qty=5, rate=200)  # 1000

		after = api.get_dashboard()["on_order"]
		self.assertEqual(after["count"], before["count"] + 1)
		self.assertAlmostEqual(after["value"], before["value"] + po.grand_total, places=2)

	def test_above_rate_kpi_flag_endpoint(self):
		# PRC-005 — a PO line priced well above its Item's linked Rate Master
		# rate lights the "Above estimated rate" KPI; a line at the threshold
		# or with no Rate Master link at all does not.
		p = self._make_project(company=self.company)
		supplier = self._supplier()
		rm = self._make_rate_master(rate=100)
		over_item = self._item(rate_master=rm.name)
		under_item = self._item(rate_master=rm.name)
		unlinked_item = self._item()  # no rate_master at all
		before = api.get_dashboard()["above_estimated_rate"]["count"]

		self._submit_po(p.name, supplier.name, over_item.name, qty=1, rate=200)  # 2x RM rate -> flagged
		self._submit_po(p.name, supplier.name, under_item.name, qty=1, rate=100)  # at RM rate -> not flagged
		self._submit_po(p.name, supplier.name, unlinked_item.name, qty=1, rate=999)  # no RM link -> not flagged

		after = api.get_dashboard()["above_estimated_rate"]["count"]
		self.assertEqual(after, before + 1)

	def test_procurement_kpi_endpoint_values(self):
		# PRC-002 — the parts of the KPI strip not covered above: a submitted
		# Purchase Receipt bumps "Received this week" and appears in the
		# recent-receipts feed with its item + status.
		p = self._make_project(company=self.company)
		supplier = self._supplier()
		item = self._item()
		before = api.get_dashboard()["received_this_week"]["count"]

		pr = self._submit_pr(p.name, supplier.name, item.name, qty=3, rate=100)

		dash = api.get_dashboard()
		self.assertEqual(dash["received_this_week"]["count"], before + 1)
		receipt = next((r for r in dash["recent_receipts"] if r["name"] == pr.name), None)
		self.assertIsNotNone(receipt)
		self.assertEqual(receipt["status"], "Full")
		self.assertEqual(receipt["item_count"], 1)
