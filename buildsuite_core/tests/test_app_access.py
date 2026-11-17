# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Who may open the BuildSuite app (api.permission): a BuildSuite role or System Manager, as
before — or a persona of any kind, including one an admin built from roles BuildSuite does not
ship. What such a user then sees is decided by the DocPerms of their roles, not here."""

import frappe

from buildsuite_core.api.permission import _has_app_permission, get_access_context
from buildsuite_core.tests.base import BuildSuiteTestCase

# An ERPNext role that is not one of BuildSuite's (BUILDSUITE_ROLES).
OTHER_ROLE = "Projects User"


class TestAppAccess(BuildSuiteTestCase):
	def _persona(self, roles, enabled=1):
		return frappe.get_doc(
			{
				"doctype": "Persona",
				"persona_name": f"Site Sales {self._n}",
				"enabled": enabled,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True)

	def _user(self, persona=None):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"access-{frappe.generate_hash(length=6)}@example.com",
				"first_name": "Access",
				"user_type": "System User",
				"send_welcome_email": 0,
				"persona": persona or "",
			}
		).insert(ignore_permissions=True)
		return user.name

	def _allowed(self, user):
		frappe.set_user(user)
		try:
			return _has_app_permission(log_denial=False)
		finally:
			frappe.set_user("Administrator")

	def test_a_persona_built_from_other_roles_opens_the_app(self):
		persona = self._persona([OTHER_ROLE])
		self.assertTrue(self._allowed(self._user(persona.name)))

	def test_a_user_with_no_persona_and_no_buildsuite_role_is_refused(self):
		user = self._user()
		frappe.get_doc("User", user).add_roles(OTHER_ROLE)
		self.assertFalse(self._allowed(user))

	def test_a_disabled_persona_does_not_open_the_app(self):
		persona = self._persona([OTHER_ROLE])
		user = self._user(persona.name)
		frappe.db.set_value("Persona", persona.name, "enabled", 0)
		self.assertFalse(self._allowed(user))

	def test_a_built_in_persona_still_opens_the_app(self):
		self.assertTrue(self._allowed(self._user("Estimator")))

	def test_the_access_payload_carries_the_persona_slug(self):
		persona = self._persona([OTHER_ROLE])
		user = self._user(persona.name)
		frappe.set_user(user)
		try:
			context = get_access_context()
		finally:
			frappe.set_user("Administrator")
		self.assertTrue(context.allowed)
		self.assertEqual(context.persona, persona.name)
		self.assertEqual(context.persona_slug, persona.slug)
		self.assertTrue(persona.slug)
