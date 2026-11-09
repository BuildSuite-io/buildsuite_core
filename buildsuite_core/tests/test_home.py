# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Home dashboard — the KPIs are scoped to the logged-in user's visible projects/tasks."""

import frappe

from buildsuite_core.api.home import get_home_dashboard
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestHomeDashboard(BuildSuiteTestCase):
	def _persona_user(self, persona, prefix):
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

	def _home_project(self, member=None, status="Ongoing"):
		doc = {
			"doctype": "Project",
			"project_name": f"HOME {frappe.generate_hash(length=5)}",
			"project_status": status,
			"company": self.company,
		}
		if member:
			doc["custom_team_members"] = [{"user": member}]
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def test_scoped_user_sees_only_their_projects(self):
		# A team-scoped persona (Site Engineer) sees only the project they're teamed on —
		# the home count must match the Projects list, not the whole company.
		se = self._persona_user("Site Engineer", "se")
		mine = self._home_project(member=se)
		self._home_project()  # another active project the user is NOT on

		frappe.set_user(se)
		try:
			dash = get_home_dashboard()
			ids = [p["id"] for p in dash["projects"]]
			self.assertIn(mine.name, ids)
			# Exactly one visible active top-level project.
			self.assertEqual(dash["kpis"]["active_projects"], 1)
		finally:
			frappe.set_user("Administrator")

	def test_admin_unscoped_sees_more_than_scoped(self):
		# Administrator is exempt from team scoping → counts both projects (plus any others);
		# the scoped user counts only the one they're teamed on.
		se = self._persona_user("Site Engineer", "se")
		self._home_project(member=se)  # the user is on this one
		self._home_project()  # …but not this one

		frappe.set_user(se)
		try:
			scoped = get_home_dashboard()["kpis"]["active_projects"]
		finally:
			frappe.set_user("Administrator")
		unscoped = get_home_dashboard()["kpis"]["active_projects"]

		self.assertEqual(scoped, 1)
		self.assertGreaterEqual(unscoped, 2)
		self.assertGreater(unscoped, scoped)

	def test_role_aware_snapshot(self):
		# A QS gets estimation/measurement tiles; the payload carries a snapshot (4), a CTA,
		# and three alert cards.
		qs = self._persona_user("Quantity Surveyor", "qs")
		frappe.set_user(qs)
		try:
			dash = get_home_dashboard()
			self.assertEqual(dash["role"], "qs")
			labels = [t["label"] for t in dash["snapshot"]]
			self.assertEqual(len(dash["snapshot"]), 4)
			for expected in ("Draft BOQs", "Approved BOQs", "MBs to certify"):
				self.assertIn(expected, labels)
			self.assertTrue(dash["cta"]["title"])
			self.assertEqual(len(dash["alerts"]), 3)
		finally:
			frappe.set_user("Administrator")

		# Administrator resolves to the org-wide 'admin' snapshot.
		frappe.set_user("Administrator")
		admin = get_home_dashboard()
		self.assertEqual(admin["role"], "admin")
		self.assertIn("Users", [t["label"] for t in admin["snapshot"]])
