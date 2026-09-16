# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""BuildSuite Workspace registry — backend-derived SPA sidebar visibility.

api.workspace_setting.get_visible_workspaces() returns the workspaces whose Visible-To roles
intersect the user's roles. This asserts, per persona, that the visible set matches the seeded
registry (the source that replaces the frontend WORKSPACE_VISIBILITY matrix), plus a few
independent exclusions the sheet mandates.
"""

import frappe

from buildsuite_core.api.workspace_setting import get_visible_workspaces, get_workspace_shortcuts
from buildsuite_core.buildsuite_core.doctype.buildsuite_workspace.seed_workspaces import (
	WORKSPACES,
	seed_workspace_shortcuts,
	seed_workspaces,
)
from buildsuite_core.permissions.resource_map import (
	RESOURCE_DOCTYPES,
	SHORTCUT_ROUTE_RESOURCES,
	route_doctype,
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
		seed_workspace_shortcuts()
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

	def test_shortcuts_are_role_filtered(self):
		# Progress Entries is restricted to admin/bsa/director/pm/site-engineer/foreman;
		# everyone else who can see the workspace sees the other four but not that one.
		def labels(persona):
			email = self._make_user(persona)
			frappe.set_user(email)
			try:
				return {s["label"] for s in get_workspace_shortcuts("site-execution")}
			finally:
				frappe.set_user("Administrator")

		foreman = labels("Foreman / Supervisor")
		self.assertIn("Progress Entries", foreman)
		self.assertIn("Projects", foreman)

		estimator = labels("Estimator")
		self.assertNotIn("Progress Entries", estimator)  # restricted, estimator excluded
		self.assertIn("Projects", estimator)  # unrestricted

	def test_shortcuts_hidden_when_workspace_not_visible(self):
		# Procurement can't see Site Execution, so even though it HAS shortcuts, none leak.
		email = self._make_user("Procurement Officer")
		frappe.set_user(email)
		try:
			self.assertEqual(get_workspace_shortcuts("site-execution"), [])
		finally:
			frappe.set_user("Administrator")

	def test_shortcut_route_resources_map_to_real_doctypes(self):
		# Drift guard: every route in the shortcut seam must resolve to a real resource key,
		# so a shortcut route can't silently fall through the read-gate (route_doctype -> None).
		bad = {k for k in SHORTCUT_ROUTE_RESOURCES.values() if k not in RESOURCE_DOCTYPES}
		self.assertFalse(bad, f"SHORTCUT_ROUTE_RESOURCES values not in RESOURCE_DOCTYPES: {bad}")
		self.assertEqual(route_doctype("/tasks"), "Task")
		self.assertEqual(route_doctype("/tasks?x=1"), "Task")  # query string ignored
		self.assertIsNone(route_doctype("/schedule"))  # not doctype-backed -> never gated

	def test_shortcut_hidden_when_doctype_unreadable(self):
		# A user may SEE a workspace yet lack read on one of its shortcut targets (the reported
		# bug: Procurement persona, Task read revoked, still saw the Task tile). Such a shortcut
		# must be hidden — mirroring the DocType-tile gate — while unrelated ones stay visible.
		# Foreman sees Site Execution but can't read Purchase Order; add a PO shortcut there.
		sc = frappe.get_doc(
			{
				"doctype": "BuildSuite Workspace Shortcut",
				"workspace": "site-execution",
				"label": "Purchase Orders (test)",
				"icon": "cart",
				"route": "/procurement/purchase-orders",
				"sort_order": 999,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
		try:
			foreman = self._make_user("Foreman / Supervisor")
			frappe.set_user(foreman)
			# precondition: the workspace is visible but the target DocType is not readable
			self.assertFalse(frappe.has_permission("Purchase Order", "read"))
			labels = {s["label"] for s in get_workspace_shortcuts("site-execution")}
			self.assertNotIn("Purchase Orders (test)", labels)
			self.assertIn("Projects", labels)  # a readable target is unaffected
			frappe.set_user("Administrator")
			admin_labels = {s["label"] for s in get_workspace_shortcuts("site-execution")}
			self.assertIn("Purchase Orders (test)", admin_labels)  # Admin reads PO -> shown
		finally:
			frappe.set_user("Administrator")
			frappe.delete_doc(
				"BuildSuite Workspace Shortcut", sc.name, ignore_permissions=True, force=True
			)
			frappe.db.commit()

	def test_ordering_is_by_sort_order(self):
		email = self._make_user("System Manager (Admin)")
		frappe.set_user(email)
		try:
			orders = [w["order"] for w in get_visible_workspaces()]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(orders, sorted(orders), "workspaces are not returned in sort order")
