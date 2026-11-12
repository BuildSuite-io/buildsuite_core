# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""A Purchase Order carries its own Terms & conditions, and its print shows them with the issuing
company's address / GSTIN / CIN / phone / email in "Ordered by"."""

import hashlib
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api.procurement_docs import get_purchase_order, save_purchase_order
from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
	_PO_PRINT_HTML,
	PO_PRINT_FORMAT,
)
from buildsuite_core.patches import refresh_purchase_order_print_format as patch_mod
from buildsuite_core.tests.base import BuildSuiteTestCase

TERMS = "<p>Payment within <b>45 days</b> of receipt.</p><ul><li>Delivery to site</li></ul>"


class TestPoTermsAndPrint(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.project = self._make_project().name
		self.company = frappe.db.get_value("Project", self.project, "company")
		self.supplier = (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": f"Terms Supplier {self._n}",
					"supplier_group": frappe.db.get_value("Supplier Group", {}, "name"),
					"supplier_type": "Company",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.item = (
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"TERMS-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
					"item_name": "Terms Item",
					"item_group": frappe.db.get_value("Item Group", {}, "name"),
					"stock_uom": "Nos",
					"is_stock_item": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _save(self, **kw):
		return save_purchase_order(
			supplier=self.supplier,
			project=self.project,
			schedule_date=add_days(nowdate(), 7),
			items=frappe.as_json([{"item_code": self.item, "qty": 2, "rate": 100}]),
			**kw,
		)

	def _html(self, name):
		frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", _PO_PRINT_HTML)
		return frappe.get_print("Purchase Order", name, print_format=PO_PRINT_FORMAT)

	# --- the form's terms -------------------------------------------------
	def test_terms_and_template_round_trip(self):
		template = (
			frappe.get_doc(
				{
					"doctype": "Terms and Conditions",
					"title": f"PO terms {self._n}",
					"custom_applicable_for": "Purchase Order",
					"terms": TERMS,
					"buying": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		po = self._save(terms=TERMS, tc_name=template)
		got = get_purchase_order(po["name"])
		self.assertEqual((got["terms"], got["tc_name"]), (TERMS, template))

	def test_saving_without_terms_keeps_them_and_an_empty_string_clears(self):
		po = self._save(terms=TERMS)
		again = save_purchase_order(
			name=po["name"],
			supplier=self.supplier,
			project=self.project,
			items=frappe.as_json([{"item_code": self.item, "qty": 3, "rate": 100}]),
		)
		self.assertEqual(again["terms"], TERMS)
		cleared = save_purchase_order(
			name=po["name"],
			supplier=self.supplier,
			project=self.project,
			terms="",
			items=frappe.as_json([{"item_code": self.item, "qty": 3, "rate": 100}]),
		)
		self.assertFalse(cleared["terms"])
		self.assertFalse(cleared["tc_name"])

	# --- the print --------------------------------------------------------
	def test_print_shows_the_pos_terms_instead_of_the_boilerplate(self):
		po = self._save(terms=TERMS)
		html = self._html(po["name"])
		self.assertIn("Payment within <b>45 days</b> of receipt.", html)
		self.assertNotIn("Part deliveries are accepted against this order", html)

	def test_print_falls_back_to_the_standard_terms_when_none_set(self):
		po = self._save()
		self.assertIn("Part deliveries are accepted against this order", self._html(po["name"]))

	def test_print_shows_the_company_block(self):
		frappe.db.set_value(
			"Company",
			self.company,
			{
				"custom_letter_head_subtext": "12 Builder Road, Pune 411001\nGSTIN 27AAAAA0000A1Z5",
				"registration_details": "U45200MH2020PTC123456",
				"phone_no": "+91 20 5550 1234",
				"email": "accounts@acme.example",
			},
		)
		html = self._html(self._save()["name"])
		for text in (
			"12 Builder Road, Pune 411001",
			"27AAAAA0000A1Z5",
			"CIN: U45200MH2020PTC123456",
			"Phone: +91 20 5550 1234",
			"Email: accounts@acme.example",
		):
			self.assertIn(text, html)

	def test_company_details_already_in_the_address_text_are_not_repeated(self):
		frappe.db.set_value(
			"Company",
			self.company,
			{"custom_letter_head_subtext": "Pune\nPhone +91 20 5550 1234", "phone_no": "+91 20 5550 1234"},
		)
		html = self._html(self._save()["name"])
		self.assertEqual(html.count("+91 20 5550 1234"), 1)

	# --- the patch --------------------------------------------------------
	def test_patch_replaces_an_unedited_format_and_leaves_an_edited_one(self):
		frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", "<p>previous seed</p>")
		with patch.object(patch_mod, "PREVIOUS_SEED_SHA1", hashlib.sha1(b"<p>previous seed</p>").hexdigest()):
			patch_mod.execute()
			self.assertEqual(frappe.db.get_value("Print Format", PO_PRINT_FORMAT, "html"), _PO_PRINT_HTML)

			frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", "<p>admin edit</p>")
			patch_mod.execute()
			self.assertEqual(
				frappe.db.get_value("Print Format", PO_PRINT_FORMAT, "html"), "<p>admin edit</p>"
			)
