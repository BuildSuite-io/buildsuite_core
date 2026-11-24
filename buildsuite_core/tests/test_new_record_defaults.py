# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The generic record form starts a new document with the values Desk gives it (Frappe's own
new-document builder), and only for a user who may create one."""

import frappe

from buildsuite_core.api.workspace_setting import new_record_defaults
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestNewRecordDefaults(BuildSuiteTestCase):
	def test_a_new_timesheet_starts_like_desk(self):
		expected = frappe.new_doc("Timesheet")
		got = new_record_defaults("Timesheet")
		self.assertEqual(got.get("naming_series"), expected.naming_series)  # a required Select's first option
		self.assertEqual(got.get("company"), expected.company)  # the user's default company
		self.assertEqual(got.get("status"), "Draft")  # a static default
		for skipped in ("name", "owner", "docstatus", "time_logs"):
			self.assertNotIn(skipped, got)

	def test_refused_without_create_permission(self):
		email = f"nrd-{self._n}-{frappe.generate_hash(length=5)}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "NRD", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		frappe.set_user(email)
		self.addCleanup(frappe.set_user, "Administrator")
		with self.assertRaises(frappe.PermissionError):
			new_record_defaults("Timesheet")
