# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Record-level permission tests (run as a specific persona via frappe.set_user).

These depend on the role DocPerms + record-level hooks seeded by
permissions/setup.py (present after migrate)."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPermissions(BuildSuiteTestCase):
	def _make_persona_user(self, persona, prefix):
		email = f"{prefix}-{self._n}@example.com"
		frappe.get_doc({
			"doctype": "User", "email": email, "first_name": prefix.upper(),
			"send_welcome_email": 0, "user_type": "System User",
			"persona": persona, "company": self.company,
		}).insert(ignore_permissions=True)
		return email

	def _project_with_member(self, user):
		return frappe.get_doc({
			"doctype": "Project", "project_name": f"PERM {self._n}",
			"custom_project_id": f"PERM-{self._n}", "project_status": "Ongoing",
			"company": self.company, "custom_team_members": [{"user": user}],
		}).insert(ignore_permissions=True)

	def test_site_engineer_edits_own_task_only(self):
		# PRM-008 — a Site Engineer can edit/delete tasks they created, not others'.
		se = self._make_persona_user("Site Engineer", "se")
		p = self._project_with_member(se)
		# A task created by Administrator (owner != SE).
		other = self._make_task(p.name)

		frappe.set_user(se)
		try:
			own = frappe.get_doc({
				"doctype": "Task", "subject": f"own {self._n}",
				"project": p.name, "task_status": "Yet To Start",
			}).insert()
			own.subject = "own edited"
			own.save()  # must not raise — SE owns it

			other_doc = frappe.get_doc("Task", other.name)
			other_doc.subject = "nope"
			self.assertRaises(frappe.PermissionError, other_doc.save)
		finally:
			frappe.set_user("Administrator")

	def test_foreman_cannot_create_project(self):
		# PRM-013 — Foreman has no Project create permission.
		fm = self._make_persona_user("Foreman / Supervisor", "fm")
		frappe.set_user(fm)
		try:
			doc = frappe.get_doc({
				"doctype": "Project", "project_name": f"FM {self._n}",
				"custom_project_id": f"FM-{self._n}", "company": self.company,
			})
			self.assertRaises(frappe.PermissionError, doc.insert)
		finally:
			frappe.set_user("Administrator")
