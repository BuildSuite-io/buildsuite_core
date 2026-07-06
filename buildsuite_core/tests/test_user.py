# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the User persona / company behaviour. Persona is a Link to the Persona
master; its roles child table drives the user's BuildSuite roles. Company is
optional for a persona'd user (the earlier mandatory-company rule was dropped)."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase

WORKFLOW_EDITOR_ROLE = "BuildSuite Project User"


class TestUserPersona(BuildSuiteTestCase):
	def _make_user(self, persona, company=None):
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"uat-{persona[:3].lower()}-{self._n}@example.com",
				"first_name": "UAT",
				"user_type": "System User",
				"send_welcome_email": 0,
				"persona": persona,
				"company": company or "",
			}
		)
		u.insert(ignore_permissions=True)
		return u

	def _roles(self, user):
		return {r.role for r in frappe.get_doc("User", user).roles}

	def test_user_persona_company_optional(self):
		u = self._make_user("Project Manager")  # must not raise with no company
		self.assertEqual(u.persona, "Project Manager")

	def test_user_persona_with_company_ok(self):
		u = self._make_user("Project Manager", company=self.company)
		self.assertEqual(u.company, self.company)

	# --- doctype-driven persona -> role sync ---------------------------------
	def test_default_personas_seeded(self):
		# The 12 defaults exist and the admin persona maps to the native role.
		self.assertGreaterEqual(frappe.db.count("Persona"), 12)
		self.assertEqual(
			frappe.db.get_value("Persona Role", {"parent": "System Manager (Admin)"}, "role"),
			"System Manager",
		)

	def test_persona_grants_its_roles(self):
		u = self._make_user("Project Manager")
		roles = self._roles(u.name)
		self.assertIn("BuildSuite PM", roles)
		self.assertIn(WORKFLOW_EDITOR_ROLE, roles)

	def test_switching_persona_swaps_the_managed_role(self):
		u = self._make_user("Project Manager")
		self.assertIn("BuildSuite PM", self._roles(u.name))
		u.persona = "Estimator"
		u.save(ignore_permissions=True)
		roles = self._roles(u.name)
		self.assertIn("BuildSuite Estimator", roles)
		self.assertNotIn("BuildSuite PM", roles)  # stale managed role dropped

	def test_system_manager_is_never_revoked_by_persona(self):
		# A persona may grant System Manager, but switching persona must not strip it.
		u = self._make_user("Project Manager")
		u.append("roles", {"role": "System Manager"})
		u.persona = "Estimator"
		u.save(ignore_permissions=True)
		self.assertIn("System Manager", self._roles(u.name))
