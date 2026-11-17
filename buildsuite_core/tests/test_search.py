# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Command palette: doctypes without a bespoke SPA place must be reachable by name."""

import frappe

from buildsuite_core.api import search as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPaletteSearch(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_supplier_and_stock_entry_open_via_generic_list(self):
		# No bespoke SPA list for these, so they must not be hidden as "covered".
		self.assertIn("Supplier", {d["doctype"] for d in api.search_doctypes("Supplier")})
		self.assertIn("Stock Entry", {d["doctype"] for d in api.search_doctypes("Stock Entry")})

	def test_doctypes_with_a_bespoke_place_stay_covered(self):
		self.assertNotIn("Customer", {d["doctype"] for d in api.search_doctypes("Customer")})
		self.assertNotIn("Purchase Order", {d["doctype"] for d in api.search_doctypes("Purchase Order")})
