# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the User persona / company behaviour. Company is optional for a
persona'd user (the earlier mandatory-company rule was dropped)."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestUserPersona(BuildSuiteTestCase):
	def test_user_persona_company_optional(self):
		u = frappe.new_doc("User")
		u.email = f"uat-{self._n}@example.com"
		u.first_name = "UAT"
		u.user_type = "System User"
		u.send_welcome_email = 0
		u.persona = "Project Manager"
		u.company = ""
		u.insert(ignore_permissions=True)  # must not raise
		self.assertEqual(u.persona, "Project Manager")

	def test_user_persona_with_company_ok(self):
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"uat-ok-{self._n}@example.com",
				"first_name": "UAT",
				"user_type": "System User",
				"send_welcome_email": 0,
				"persona": "Project Manager",
				"company": self.company,
			}
		)
		u.insert(ignore_permissions=True)
		self.assertEqual(u.company, self.company)
