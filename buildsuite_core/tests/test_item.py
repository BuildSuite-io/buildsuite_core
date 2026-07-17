# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the Item.custom_rate_master link — BuildSuite's estimation-side
tie between an ERPNext Item and its Construction Rate Master resource."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestItem(BuildSuiteTestCase):
	def _make_item(self, rate_master=None):
		return frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"UAT-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
				"item_name": "UAT Item",
				"item_group": frappe.db.get_value("Item Group", {}, "name"),
				"stock_uom": "Nos",
				"custom_rate_master": rate_master,
			}
		).insert(ignore_permissions=True)

	def test_item_rate_master_link_field(self):
		# EST-026 / BUY-019 — Item carries a Rate Master link field, and it
		# persists once set.
		rm = self._make_rate_master(rate=250)
		item = self._make_item(rate_master=rm.name)
		self.assertEqual(item.custom_rate_master, rm.name)

	def test_many_items_map_to_one_rate_master_resource(self):
		# BUY-020 — several Items can all link to the SAME resource; the
		# relationship is many-Items-to-one-resource, not exclusive.
		rm = self._make_rate_master(rate=300)
		i1 = self._make_item(rate_master=rm.name)
		i2 = self._make_item(rate_master=rm.name)
		self.assertEqual(i1.custom_rate_master, rm.name)
		self.assertEqual(i2.custom_rate_master, rm.name)
		self.assertNotEqual(i1.name, i2.name)
