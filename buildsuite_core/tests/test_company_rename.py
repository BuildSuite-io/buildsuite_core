# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Renaming a company: the name really changes (it can't be edited in place) and the company's
Letter Head follows the new name."""

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.api.company import rename_company
from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
	letter_head_name,
	rebuild_letter_head,
)
from buildsuite_core.utils.project import default_company

NEW_NAME = "Renamed Builders Ltd"


class TestCompanyRename(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		default = default_company()
		self.company = frappe.db.get_value("Company", {"name": ["!=", default]}, "name")
		self.default = default
		rebuild_letter_head(self.company)

	def tearDown(self):
		frappe.db.rollback()

	def test_rename_changes_the_name_and_rebuilds_the_letter_head(self):
		old_head = letter_head_name(self.company)
		self.assertTrue(frappe.db.exists("Letter Head", old_head))

		result = rename_company(self.company, NEW_NAME)

		self.assertEqual(result["company"], NEW_NAME)
		self.assertEqual(frappe.db.get_value("Company", NEW_NAME, "company_name"), NEW_NAME)
		new_head = letter_head_name(NEW_NAME)
		self.assertIn(NEW_NAME, frappe.db.get_value("Letter Head", new_head, "content"))
		self.assertFalse(frappe.db.exists("Letter Head", old_head), "the old head is dropped")

	def test_default_company_keeps_its_head_with_the_new_name(self):
		rename_company(self.default, NEW_NAME)
		head = letter_head_name(NEW_NAME)
		self.assertEqual(head, "BuildSuite Standard")
		self.assertIn(NEW_NAME, frappe.db.get_value("Letter Head", head, "content"))

	def test_a_taken_or_empty_name_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			rename_company(self.company, self.default)
		with self.assertRaises(frappe.ValidationError):
			rename_company(self.company, "  ")
