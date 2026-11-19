# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""A Purchase Order's optional site contact: saved from the form, returned with the contact's
name and mobile, and printed with them under "Deliver to project"."""

import hashlib

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api.procurement_docs import get_purchase_order, save_purchase_order
from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
	_PO_PRINT_HTML,
	PO_PRINT_FORMAT,
)
from buildsuite_core.patches import add_po_site_contact_to_print_format as patch_mod
from buildsuite_core.tests.base import BuildSuiteTestCase

MOBILE = "+91 98765 43210"


class TestPoSiteContact(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.project = self._make_project().name
		self.supplier = (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": f"Contact Supplier {self._n}",
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
					"item_code": f"CONTACT-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
					"item_name": "Contact Item",
					"item_group": frappe.db.get_value("Item Group", {}, "name"),
					"stock_uom": "Nos",
					"is_stock_item": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.contact = self._user("Ravi Site", MOBILE)

	def _user(self, first_name, mobile="", enabled=1):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"site-contact-{frappe.generate_hash(length=8)}@example.com",
					"first_name": first_name,
					"mobile_no": mobile,
					"enabled": enabled,
					"send_welcome_email": 0,
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

	def test_site_contact_round_trips_with_name_and_mobile(self):
		po = self._save(site_contact=self.contact)
		self.assertEqual(
			get_purchase_order(po["name"])["site_contact"],
			{"user": self.contact, "full_name": "Ravi Site", "mobile_no": MOBILE},
		)

	def test_saving_without_it_keeps_the_contact_and_an_empty_string_clears(self):
		po = self._save(site_contact=self.contact)
		kept = self._save(name=po["name"])
		self.assertEqual(kept["site_contact"]["user"], self.contact)
		cleared = self._save(name=po["name"], site_contact="")
		self.assertIsNone(cleared["site_contact"])

	def test_a_disabled_user_cannot_be_the_site_contact(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(site_contact=self._user("Gone", enabled=0))

	def test_print_shows_the_site_contact_with_mobile(self):
		html = self._html(self._save(site_contact=self.contact)["name"])
		self.assertIn("Site contact:", html)
		self.assertIn("Ravi Site", html)
		self.assertIn(MOBILE, html)

	def test_print_leaves_the_line_out_without_a_contact(self):
		self.assertNotIn("Site contact:", self._html(self._save()["name"]))

	def test_patch_replaces_an_unedited_format_and_leaves_an_edited_one(self):
		previous = "<p>previous seed</p>"
		frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", previous)
		patch_mod.PREVIOUS_SEED_SHA1, original = (
			hashlib.sha1(previous.encode()).hexdigest(),
			patch_mod.PREVIOUS_SEED_SHA1,
		)
		self.addCleanup(setattr, patch_mod, "PREVIOUS_SEED_SHA1", original)
		patch_mod.execute()
		self.assertEqual(frappe.db.get_value("Print Format", PO_PRINT_FORMAT, "html"), _PO_PRINT_HTML)

		frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", "<p>admin edit</p>")
		patch_mod.execute()
		self.assertEqual(frappe.db.get_value("Print Format", PO_PRINT_FORMAT, "html"), "<p>admin edit</p>")
