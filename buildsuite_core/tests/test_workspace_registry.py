# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""BuildSuite Workspace registry — backend-derived SPA sidebar visibility.

api.workspace_setting.get_visible_workspaces() returns the workspaces whose Visible-To roles
intersect the user's roles. This asserts, per persona, that the visible set matches the seeded
registry (the source that replaces the frontend WORKSPACE_VISIBILITY matrix), plus a few
independent exclusions the sheet mandates.
"""

import frappe

from buildsuite_core.api.workspace_setting import get_visible_workspaces
from buildsuite_core.buildsuite_core.doctype.buildsuite_workspace.seed_workspaces import (
	WORKSPACES,
	seed_workspaces,
)
from buildsuite_core.tests.test_permission_matrix import _PersonaBase

# persona record name -> the slug used in the registry seed.
PERSONA_SLUG = {
	"Director / Owner": "director",
	"Project Manager": "pm",
	"Estimator": "estimator",
	"Quantity Surveyor": "qs",
	"Site Engineer": "site-engineer",
	"Foreman / Supervisor": "foreman",
	"Procurement Officer": "procurement",
	"Store Keeper": "store-keeper",
	"Accountant": "accountant",
	"HR Manager": "hr-manager",
	"System Manager (Admin)": "admin",
	"BuildSuite Administrator": "bsa",
}


def _expected_slugs(persona_slug):
	return {ws["slug"] for ws in WORKSPACES if persona_slug in ws["visibility"]}


class TestWorkspaceRegistry(_PersonaBase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The roles must exist for the registry's Visible-To links to resolve.
		from buildsuite_core.permissions.setup import setup_record_permissions

		setup_record_permissions()
		seed_workspaces()
		frappe.db.commit()
		frappe.clear_cache()

	def _visible(self, email):
		frappe.set_user(email)
		try:
			return {w["slug"] for w in get_visible_workspaces()}
		finally:
			frappe.set_user("Administrator")

	def test_each_persona_sees_exactly_its_registry_workspaces(self):
		for persona, slug in PERSONA_SLUG.items():
			email = self._make_user(persona)
			with self.subTest(persona=persona):
				self.assertEqual(
					self._visible(email),
					_expected_slugs(slug),
					f"{persona} visible workspaces drifted from the registry",
				)

	def test_admin_sees_all_twelve(self):
		email = self._make_user("System Manager (Admin)")
		self.assertEqual(len(self._visible(email)), len(WORKSPACES))

	def test_independent_exclusions(self):
		# Straight from the WORKSPACE_VISIBILITY sheet — hard "must not see" cases.
		cases = {
			"Estimator": {"exclude": {"procurement", "workforce", "equipment", "accounting"}},
			"Procurement Officer": {"exclude": {"estimation"}},
			"HR Manager": {"exclude": {"estimation", "subcontract", "equipment", "accounting"}},
			"Foreman / Supervisor": {"exclude": {"estimation", "subcontract", "accounting", "buying", "stock"}},
		}
		for persona, spec in cases.items():
			email = self._make_user(persona)
			visible = self._visible(email)
			for slug in spec["exclude"]:
				with self.subTest(persona=persona, slug=slug):
					self.assertNotIn(slug, visible, f"{persona} must NOT see {slug}")

	def test_access_hint_reflects_the_persona(self):
		# The cosmetic hint returned per workspace matches the sheet for the persona.
		def hint(email, slug):
			frappe.set_user(email)
			try:
				return next((w["access"] for w in get_visible_workspaces() if w["slug"] == slug), None)
			finally:
				frappe.set_user("Administrator")

		est = self._make_user("Estimator")
		self.assertEqual(hint(est, "site-execution"), "read")
		self.assertEqual(hint(est, "estimation"), "full")
		fore = self._make_user("Foreman / Supervisor")
		self.assertEqual(hint(fore, "procurement"), "create-own")
		self.assertEqual(hint(fore, "project-finance"), "self-service")

	def test_ordering_is_by_sort_order(self):
		email = self._make_user("System Manager (Admin)")
		frappe.set_user(email)
		try:
			orders = [w["order"] for w in get_visible_workspaces()]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(orders, sorted(orders), "workspaces are not returned in sort order")
