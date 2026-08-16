# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the Subcontractor master — a native Supplier tagged
supplier_type="Subcontractor" (api/subcontract.py's list/get/create/update
endpoints, which own the join with its primary Contact)."""

import frappe

from buildsuite_core.api import subcontract as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestSubcontractor(BuildSuiteTestCase):
	def _subcontractor(self):
		"""A subcontractor is a native Supplier tagged supplier_type='Subcontractor'."""
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"Sub {self._n}",
				"supplier_type": "Subcontractor",
				"supplier_group": "Subcontractor",
				"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
			}
		).insert(ignore_permissions=True)

	def test_create_subcontractor_tags_supplier_type_and_group(self):
		trade = frappe.db.get_value("Construction Trade", {}, "name")
		out = api.create_subcontractor(subcontractor_name=f"UAT Sub {self._n}", trade=trade, tax_id="TAX-123")
		self.assertEqual(out["trade"], trade)
		self.assertEqual(out["tax_id"], "TAX-123")
		self.assertEqual(out["status"], "Active")
		doc = frappe.get_doc("Supplier", out["name"])
		self.assertEqual(doc.supplier_type, "Subcontractor")
		self.assertEqual(doc.supplier_group, "Subcontractor")

	def test_create_subcontractor_upserts_primary_contact(self):
		out = api.create_subcontractor(
			subcontractor_name=f"UAT Sub {self._n}",
			contact_person="Ravi",
			phone="9999999999",
			email="ravi@example.com",
		)
		self.assertEqual(out["contact_person"], "Ravi")
		self.assertEqual(out["phone"], "9999999999")
		self.assertEqual(out["email"], "ravi@example.com")

	def test_update_subcontractor_updates_fields_and_contact(self):
		sub = self._subcontractor()
		out = api.update_subcontractor(
			sub.name,
			subcontractor_name="Renamed Sub",
			tax_id="TAX-999",
			status="Inactive",
			contact_person="Ravi",
			phone="2222222222",
			email="b@x.com",
		)
		self.assertEqual(out["subcontractor_name"], "Renamed Sub")
		self.assertEqual(out["tax_id"], "TAX-999")
		self.assertEqual(out["status"], "Inactive")
		self.assertEqual(out["contact_person"], "Ravi")
		self.assertEqual(out["phone"], "2222222222")

		# Updating contact info again edits the SAME Contact, not a second one.
		api.update_subcontractor(sub.name, contact_person="Ravi K", phone="3333333333", email="c@x.com")
		contacts = frappe.get_all(
			"Dynamic Link",
			filters={"link_doctype": "Supplier", "link_name": sub.name, "parenttype": "Contact"},
			pluck="parent",
		)
		self.assertEqual(len(contacts), 1)

	def test_subcontractor_status_reflects_disabled_flag(self):
		sub = self._subcontractor()
		self.assertEqual(api.get_subcontractor(sub.name)["status"], "Active")
		api.update_subcontractor(sub.name, status="Inactive")
		self.assertEqual(api.get_subcontractor(sub.name)["status"], "Inactive")
		api.update_subcontractor(sub.name, status="Active")
		self.assertEqual(api.get_subcontractor(sub.name)["status"], "Active")

	def test_list_subcontractors_excludes_other_supplier_types(self):
		sub = self._subcontractor()
		other = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"Regular Supplier {self._n}",
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)
		names = {s["name"] for s in api.list_subcontractors()}
		self.assertIn(sub.name, names)
		self.assertNotIn(other.name, names)
