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

	def test_unknown_persona_is_rejected(self):
		# Frappe's Link validation blocks assigning a persona that doesn't exist, so a
		# user can never be left pointing at a missing persona (and thus silently
		# stripped of their roles). The sync hook also guards against it defensively.
		u = self._make_user("BuildSuite Administrator")
		u.persona = "No Such Persona"
		with self.assertRaises(frappe.LinkValidationError):
			u.save(ignore_permissions=True)

	def test_admin_personas_are_backend_only(self):
		# The two admin personas are flagged backend-only, so they're excluded from
		# the app's assignable set (enabled + not backend_only) that the user-form
		# link picker queries — they can only be assigned from the Frappe desk.
		for name in ("System Manager (Admin)", "BuildSuite Administrator"):
			self.assertEqual(frappe.db.get_value("Persona", name, "backend_only"), 1)
		assignable = frappe.get_all(
			"Persona", filters={"enabled": 1, "backend_only": 0}, pluck="name"
		)
		self.assertNotIn("BuildSuite Administrator", assignable)
		self.assertNotIn("System Manager (Admin)", assignable)
		self.assertIn("Project Manager", assignable)

	def test_repair_reenables_disabled_default_personas(self):
		# The repair restores a default persona that was left disabled — so it
		# reappears in the enabled-only user-form picker.
		from buildsuite_core.api.users import list_personas
		from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import (
			repair_default_personas,
		)

		frappe.db.set_value("Persona", "BuildSuite Administrator", "enabled", 0)
		self.assertNotIn(
			"BuildSuite Administrator", [p["name"] for p in list_personas()]
		)
		repair_default_personas()
		self.assertEqual(frappe.db.get_value("Persona", "BuildSuite Administrator", "enabled"), 1)
		self.assertIn("BuildSuite Administrator", [p["name"] for p in list_personas()])
