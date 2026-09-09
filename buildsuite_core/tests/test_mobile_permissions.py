# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The companion mobile app's extra DocPerms (setup_mobile_permissions) — layered on the base
matrix without revoking it. Source: the mobile-permissions sheet."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestMobilePermissions(BuildSuiteTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Seed just the mobile layer (fast). The base matrix is already present on any migrated
		# site; setup_mobile only upgrades, so it's enough to assert the mobile grants + that the
		# base Field Attendance grant survives the layering.
		from buildsuite_core.permissions.setup import setup_mobile_permissions

		setup_mobile_permissions()
		frappe.db.commit()  # noqa: bs-manual-commit — seed once for the whole class

	def _perm(self, doctype, role, ptype):
		return frappe.db.get_value(
			"Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}, ptype
		)

	def test_site_engineer_full_material_request(self):
		for p in ("select", "read", "write", "create", "submit", "cancel"):
			self.assertTrue(self._perm("Material Request", "BuildSuite Site Engineer", p), p)

	def test_foreman_full_stock_entry(self):
		for p in ("read", "write", "create", "submit", "cancel"):
			self.assertTrue(self._perm("Stock Entry", "BuildSuite Foreman", p), p)

	def test_pm_full_purchase_receipt(self):
		for p in ("read", "write", "create", "submit", "cancel"):
			self.assertTrue(self._perm("Purchase Receipt", "BuildSuite PM", p), p)

	def test_engineer_task_progress_entry_crw(self):
		for p in ("read", "write", "create"):
			self.assertTrue(self._perm("Task Progress Entry", "BuildSuite Site Engineer", p), p)

	def test_read_only_grants(self):
		# Journal Entry / Item / UOM are read+select only for the mobile roles.
		self.assertTrue(self._perm("Journal Entry", "BuildSuite Site Engineer", "read"))
		self.assertFalse(self._perm("Journal Entry", "BuildSuite Site Engineer", "write"))
		self.assertTrue(self._perm("UOM", "BuildSuite Foreman", "select"))

	def test_field_attendance_registers_full_for_creators(self):
		for dt in ("Field Attendance", "Labour Attendance Register", "Overtime Attendance Register"):
			self.assertTrue(self._perm(dt, "BuildSuite HR Manager", "create"), dt)

	def test_layering_does_not_revoke_base(self):
		# The base matrix grants the Foreman create on Field Attendance — the mobile layer must
		# keep it (upgrade-only), never zero it out.
		self.assertTrue(self._perm("Field Attendance", "BuildSuite Foreman", "create"))
