# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""A company's brand colour: saved through update_company_branding (admin only, validated),
returned by list_companies / company_branding, and cleared back to "derive from the ID"."""

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.api.company import (
	company_branding,
	list_companies,
	update_company_branding,
)


class TestCompanyBrandColour(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.company = frappe.db.get_value("Company", {}, "name")
		self.original = frappe.db.get_value("Company", self.company, "custom_brand_colour")

	def tearDown(self):
		frappe.db.set_value("Company", self.company, "custom_brand_colour", self.original)
		frappe.set_user("Administrator")

	def _colour_in_list(self):
		return next(c["colour"] for c in list_companies() if c["id"] == self.company)

	def test_colour_round_trips_through_branding_and_the_company_list(self):
		update_company_branding(company=self.company, brand_colour="Rose")
		self.assertEqual(company_branding(self.company)["brand_colour"], "Rose")
		self.assertEqual(self._colour_in_list(), "Rose")

	def test_empty_colour_clears_it_so_the_ui_derives_one(self):
		update_company_branding(company=self.company, brand_colour="Blue")
		update_company_branding(company=self.company, brand_colour="")
		self.assertEqual(self._colour_in_list(), "")

	def test_omitting_the_colour_leaves_it_alone(self):
		update_company_branding(company=self.company, brand_colour="Amber")
		update_company_branding(company=self.company, letter_head_subtext="Tel 123")
		self.assertEqual(self._colour_in_list(), "Amber")

	def test_unknown_colour_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			update_company_branding(company=self.company, brand_colour="Chartreuse")

	def test_non_admin_cannot_set_it(self):
		user = "test-brand-colour@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Brand", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(user)
		with self.assertRaises(frappe.PermissionError):
			update_company_branding(company=self.company, brand_colour="Cyan")
