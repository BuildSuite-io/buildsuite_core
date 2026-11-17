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

	def test_admin_sees_all_workspaces(self):
		email = self._make_user("System Manager (Admin)")
		self.assertEqual(len(self._visible(email)), len(WORKSPACES))

	def test_independent_exclusions(self):
		# Straight from the WORKSPACE_VISIBILITY sheet — hard "must not see" cases.
		cases = {
			"Estimator": {"exclude": {"sales", "procurement", "workforce", "equipment", "accounting"}},
			"Procurement Officer": {"exclude": {"estimation"}},
			"HR Manager": {"exclude": {"estimation", "subcontract", "equipment", "accounting"}},
			"Foreman / Supervisor": {
				"exclude": {"estimation", "subcontract", "accounting", "buying", "stock"}
			},
		}
		for persona, spec in cases.items():
			email = self._make_user(persona)
			visible = self._visible(email)
			for slug in spec["exclude"]:
				with self.subTest(persona=persona, slug=slug):
					self.assertNotIn(slug, visible, f"{persona} must NOT see {slug}")

		director = self._make_user("Director / Owner")
		admin = self._make_user("System Manager (Admin)")
		bsa = self._make_user("BuildSuite Administrator")
		for email in (director, admin, bsa):
			self.assertIn("sales", self._visible(email))

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

	def _shortcut_labels(self, user):
		frappe.set_user(user)
		try:
			return {s["label"] for s in get_workspace_shortcuts("site-execution")}
		finally:
			frappe.set_user("Administrator")

	def test_shortcuts_follow_read_permission_not_role_lists(self):
		# Who sees a shortcut is Frappe permissions on what it opens: the Progress Entries tile
		# shows exactly to the personas that can read Task Progress Entry.
		for persona in ("Foreman / Supervisor", "Estimator", "Quantity Surveyor", "Accountant"):
			user = self._make_user(persona)
			frappe.set_user(user)
			try:
				can_read = frappe.has_permission("Task Progress Entry", "read")
			finally:
				frappe.set_user("Administrator")
			labels = self._shortcut_labels(user)
			self.assertEqual("Progress Entries" in labels, bool(can_read), persona)
			self.assertIn("Projects", labels, persona)

	def test_granting_read_in_role_permission_manager_shows_the_tile(self):
		# A role BuildSuite does not ship: once given read on Task Progress Entry (and a view
		# of the workspace), its users get the tile — no shortcut configuration involved.
		from frappe.permissions import add_permission, update_permission_property

		self.addCleanup(frappe.clear_cache)  # runs after the rollback, so no grant stays cached
		role = f"Shortcut Test {frappe.generate_hash(length=5)}"
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
			ignore_permissions=True
		)
		ws = frappe.get_doc("BuildSuite Workspace", "site-execution")
		ws.append("roles", {"role": role, "access": "read"})
		ws.save(ignore_permissions=True)
		user = self._make_user("Estimator")
		frappe.get_doc("User", user).add_roles(role)

		add_permission("Task Progress Entry", role, 0)
		update_permission_property("Task Progress Entry", role, 0, "read", 1, validate=False)
		frappe.clear_cache()
		self.assertIn("Progress Entries", self._shortcut_labels(user))

	def test_a_leftover_restriction_row_is_ignored(self):
		# Rows from the retired "Restrict To Roles" list must not hide a tile.
		sc = frappe.db.get_value(
			"BuildSuite Workspace Shortcut", {"workspace": "site-execution", "label": "Projects"}
		)
		frappe.get_doc(
			{
				"doctype": "BuildSuite Workspace Role",
				"parent": sc,
				"parenttype": "BuildSuite Workspace Shortcut",
				"parentfield": "roles",
				"role": "System Manager",
			}
		).db_insert()
		self.assertIn("Projects", self._shortcut_labels(self._make_user("Foreman / Supervisor")))

	def test_the_patch_removes_only_shortcut_restriction_rows(self):
		from buildsuite_core.patches.drop_workspace_shortcut_role_restrictions import execute

		sc = frappe.db.get_value(
			"BuildSuite Workspace Shortcut", {"workspace": "site-execution", "label": "Tasks"}
		)
		frappe.get_doc(
			{
				"doctype": "BuildSuite Workspace Role",
				"parent": sc,
				"parenttype": "BuildSuite Workspace Shortcut",
				"parentfield": "roles",
				"role": "System Manager",
			}
		).db_insert()
		workspace_roles = frappe.db.count("BuildSuite Workspace Role", {"parenttype": "BuildSuite Workspace"})
		execute()
		self.assertEqual(
			frappe.db.count("BuildSuite Workspace Role", {"parenttype": "BuildSuite Workspace Shortcut"}), 0
		)
		self.assertEqual(
			frappe.db.count("BuildSuite Workspace Role", {"parenttype": "BuildSuite Workspace"}),
			workspace_roles,
		)

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
		self.assertEqual(route_doctype("/schedule"), "Task")  # the schedule shows the tasks

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
			frappe.delete_doc("BuildSuite Workspace Shortcut", sc.name, ignore_permissions=True, force=True)
			frappe.db.commit()

	def test_ordering_is_by_sort_order(self):
		email = self._make_user("System Manager (Admin)")
		frappe.set_user(email)
		try:
			orders = [w["order"] for w in get_visible_workspaces()]
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(orders, sorted(orders), "workspaces are not returned in sort order")
