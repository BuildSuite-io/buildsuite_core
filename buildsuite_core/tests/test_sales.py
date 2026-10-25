# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Owner-only Sales payment schedule templates."""

import frappe

from buildsuite_core.api.sales import (
	delete_payment_terms_template,
	list_payment_terms_templates,
	payment_terms_access,
	save_payment_terms_template,
)
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestSalesPaymentTerms(BuildSuiteTestCase):
	def _user(self, role):
		email = f"sales-{frappe.generate_hash(length=5)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Sales",
				"user_type": "System User",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
		return email

	def test_owner_can_create_list_and_delete_template(self):
		user = self._user("BuildSuite Director")
		frappe.set_user(user)
		try:
			self.assertTrue(payment_terms_access()["can_create"])
			template = save_payment_terms_template(
				title=f"Stage schedule {frappe.generate_hash(length=4)}",
				milestones=[
					{
						"milestone": "Foundation",
						"trigger": "stage",
						"stage_key": "Foundation",
						"percent": 40,
						"certify": 1,
					},
					{
						"milestone": "Final",
						"trigger": "date",
						"days_after": 90,
						"percent": 60,
					},
				],
			)
			self.assertEqual(len(template["rows"]), 2)
			self.assertEqual(template["rows"][0]["stage_key"], "Foundation")
			self.assertIn(template["id"], [row["id"] for row in list_payment_terms_templates()])
			self.assertEqual(delete_payment_terms_template(template["id"]), {"ok": True})
		finally:
			frappe.set_user("Administrator")

	def test_non_owner_cannot_read_or_create_templates(self):
		user = self._user("BuildSuite PM")
		frappe.set_user(user)
		try:
			self.assertFalse(payment_terms_access()["can_read"])
			with self.assertRaises(frappe.PermissionError):
				list_payment_terms_templates()
			with self.assertRaises(frappe.PermissionError):
				save_payment_terms_template(title="Not allowed")
		finally:
			frappe.set_user("Administrator")

	def test_invalid_milestone_values_are_rejected(self):
		user = self._user("BuildSuite Director")
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.ValidationError):
				save_payment_terms_template(
					title=f"Invalid schedule {frappe.generate_hash(length=4)}",
					milestones=[{"milestone": "Bad", "trigger": "unknown", "percent": 110}],
				)
		finally:
			frappe.set_user("Administrator")
