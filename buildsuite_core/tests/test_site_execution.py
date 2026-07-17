# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the Site Execution workspace's configurable report list
(api/site_execution.py) -- the one piece of "workspace customization" that's
actually backend-authored and server-testable in this app."""

import frappe

from buildsuite_core.api import site_execution as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestSiteExecutionWorkspace(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self._original_reports = [
			{"report": r.report, "icon": r.icon, "description": r.description}
			for r in frappe.get_single("Site Execution Settings").reports
		]
		self.addCleanup(self._restore_reports)

	def _restore_reports(self):
		frappe.set_user("Administrator")
		api.set_site_execution_reports(reports=self._original_reports)

	def _a_report(self):
		return frappe.db.get_value("Report", {"disabled": 0}, "name")

	def _make_persona_user(self, persona, prefix):
		email = f"{prefix}-{self._n}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": prefix.upper(),
				"send_welcome_email": 0,
				"user_type": "System User",
				"persona": persona,
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		return email

	def test_workspace_custom_config_persists(self):
		# WSC-011 -- the configured report list is actually written to the
		# Single doctype and read back the same on a fresh call (not just held
		# in the caller's in-memory doc).
		report = self._a_report()
		if not report:
			self.skipTest("No Report records on this site to configure")
		api.set_site_execution_reports(reports=[{"report": report, "icon": "star", "description": "UAT"}])
		fetched = api.get_site_execution_reports()
		self.assertEqual(len(fetched), 1)
		self.assertEqual(fetched[0]["report"], report)
		self.assertEqual(fetched[0]["icon"], "star")

	def test_only_configurer_role_can_add_workspace_links(self):
		# WSC-013 -- only an admin role (System Manager / BuildSuite
		# Administrator) can change the workspace's report list; anyone else is
		# rejected before anything is written.
		fm = self._make_persona_user("Foreman / Supervisor", "wscfm")
		frappe.set_user(fm)
		try:
			self.assertRaises(
				frappe.PermissionError, api.set_site_execution_reports, reports=[]
			)
		finally:
			frappe.set_user("Administrator")
