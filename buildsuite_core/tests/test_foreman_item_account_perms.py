# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

ROLES = ("BuildSuite Site Engineer", "BuildSuite Foreman", "BuildSuite Procurement Officer")


def _perm(doctype, role):
	return frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": 0},
		["select", "read", "write", "create"],
		as_dict=True,
	)


class TestForemanItemAccountPerms(IntegrationTestCase):
	def test_account_select_read_for_field_roles(self):
		for role in ROLES:
			p = _perm("Account", role)
			self.assertTrue(p and p.select and p.read, role)
			self.assertFalse(p.write or p.create, role)

	def test_foreman_item_select_read_in_seed_matrix(self):
		from buildsuite_core.permissions.setup import ITEM_ROLE_PERMS

		perms = ITEM_ROLE_PERMS["BuildSuite Foreman"]
		self.assertTrue(perms.get("select") and perms.get("read"))
		self.assertFalse(perms.get("write") or perms.get("create"))

	def test_foreman_item_select_read_applied(self):
		from buildsuite_core.patches.grant_foreman_item_select_read import execute

		execute()
		p = _perm("Item", "BuildSuite Foreman")
		self.assertTrue(p.select and p.read)
		self.assertFalse(p.write or p.create)
		engineer = _perm("Item", "BuildSuite Site Engineer")
		self.assertTrue(engineer.select and engineer.read)
