# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The self-service app-icon diagnostics endpoint (api.diagnostics)."""

import frappe

from buildsuite_core.api.diagnostics import app_icon_diagnostics
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestDiagnostics(BuildSuiteTestCase):
	def test_report_shape(self):
		frappe.set_user("Administrator")
		d = app_icon_diagnostics()
		for key in ("versions", "apps_screen", "logo_asset", "new_nav", "legacy_workspace", "hints"):
			self.assertIn(key, d)
		self.assertIsInstance(d["hints"], list)
		# The /apps hook section names the app and whether it's listed for this user.
		self.assertIn("add_to_apps_screen_hook", d["apps_screen"])

	def test_admin_only(self):
		email = "diag_noadmin_%s@example.com" % frappe.generate_hash(length=5)
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "NoAdmin",
				"send_welcome_email": 0,
				"roles": [{"role": "BuildSuite Estimator"}],
			}
		).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				app_icon_diagnostics()
		finally:
			frappe.set_user("Administrator")
