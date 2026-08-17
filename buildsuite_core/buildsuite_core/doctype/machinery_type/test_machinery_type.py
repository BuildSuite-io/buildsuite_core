# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.tests.base import BuildSuiteTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestMachineryType(IntegrationTestCase):
	"""
	Integration tests for MachineryType.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestMachineryType(BuildSuiteTestCase):
	def _type(self, name=None):
		return frappe.get_doc(
			{
				"doctype": "Machinery Type",
				"type_name": name or f"UAT Type {frappe.generate_hash(length=6)}",
			}
		).insert(ignore_permissions=True)

	def test_type_name_is_mandatory(self):
		# type_name also drives autoname ("field:type_name"), so a blank value is
		# rejected during naming as a plain ValidationError, not MandatoryError.
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Machinery Type"}).insert(ignore_permissions=True)

	def test_type_name_is_unique_and_is_the_record_name(self):
		mt = self._type("UAT Excavator")
		self.assertEqual(mt.name, "UAT Excavator")
		with self.assertRaises(frappe.DuplicateEntryError):
			self._type("UAT Excavator")

	def test_delete_unreferenced_type(self):
		mt = self._type()
		frappe.delete_doc("Machinery Type", mt.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Machinery Type", mt.name))

	def test_type_referenced_by_machinery_is_link_protected(self):
		mt = self._type()
		frappe.get_doc(
			{
				"doctype": "Machinery",
				"machinery_name": "UAT Machine",
				"machinery_type": mt.name,
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Machinery Type", mt.name, ignore_permissions=True)
