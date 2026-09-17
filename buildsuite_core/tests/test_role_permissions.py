# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Admin actions for the BuildSuite default role-permission matrix (api.role_permissions)."""

import frappe

from buildsuite_core.api.role_permissions import (
	export_role_permissions,
	restore_default_role_permissions,
)
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestRolePermissionActions(BuildSuiteTestCase):
	def _non_admin_user(self):
		email = "perm_noadmin_%s@example.com" % frappe.generate_hash(length=5)
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "NoAdmin",
				"send_welcome_email": 0,
				"roles": [{"role": "BuildSuite Estimator"}],
			}
		).insert(ignore_permissions=True)
		return email

	def test_export_returns_current_buildsuite_docperms(self):
		frappe.set_user("Administrator")
		exp = export_role_permissions()
		# Shape
		self.assertIn("BuildSuite Procurement Officer", exp["roles"])
		self.assertIsInstance(exp["permissions"], dict)
		# A known managed doctype is present with the PO's full+submit grant
		self.assertIn("Material Request", exp["permissions"])
		po = next(
			r for r in exp["permissions"]["Material Request"]
			if r["role"] == "BuildSuite Procurement Officer"
		)
		self.assertEqual(po["read"], 1)
		self.assertEqual(po["create"], 1)
		self.assertEqual(po["submit"], 1)
		# Only BuildSuite roles are exported (System Manager's blanket grant is excluded)
		exported_roles = {r["role"] for rows in exp["permissions"].values() for r in rows}
		self.assertTrue(exported_roles <= set(exp["roles"]))
		self.assertNotIn("System Manager", exported_roles)

	def test_actions_are_admin_only(self):
		# _require_admin raises before any work (so this never triggers the heavy re-apply).
		email = self._non_admin_user()
		frappe.set_user(email)
		try:
			with self.assertRaises(frappe.PermissionError):
				restore_default_role_permissions()
			with self.assertRaises(frappe.PermissionError):
				export_role_permissions()
		finally:
			frappe.set_user("Administrator")

	def test_restore_reapplies_a_default_grant(self):
		# The full restore_role_permissions() is minutes-long (the child-table read mirror), so we
		# exercise the mechanism on one doctype group: tamper a grant, re-apply just that slice
		# (exactly what restore_role_permissions runs for Material Request), assert the default
		# is back.
		frappe.set_user("Administrator")
		from frappe.permissions import update_permission_property

		from buildsuite_core.permissions.setup import setup_purchase_stock_permissions

		flt = {
			"parent": "Material Request",
			"role": "BuildSuite Procurement Officer",
			"permlevel": 0,
		}
		update_permission_property(
			"Material Request", "BuildSuite Procurement Officer", 0, "create", 0, validate=False
		)
		frappe.clear_cache()
		self.assertFalse(frappe.db.get_value("Custom DocPerm", flt, "create"))

		setup_purchase_stock_permissions()
		self.assertTrue(frappe.db.get_value("Custom DocPerm", flt, "create"))
