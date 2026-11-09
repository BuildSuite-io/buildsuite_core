# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.api import equipment as api
from buildsuite_core.tests.base import BuildSuiteTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestMachinery(IntegrationTestCase):
	"""
	Integration tests for Machinery.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestMachinery(BuildSuiteTestCase):
	"""The Machinery register (equipment master) and its dashboard/KPI feed
	(api/equipment.py get_dashboard)."""

	def _machinery_type(self):
		return frappe.get_doc(
			{"doctype": "Machinery Type", "type_name": f"UAT Type {frappe.generate_hash(length=5)}"}
		).insert(ignore_permissions=True)

	def _machinery(self, **kw):
		mtype = kw.pop("machinery_type", None) or self._machinery_type().name
		fields = {
			"doctype": "Machinery",
			"machinery_name": f"UAT Machine {frappe.generate_hash(length=5)}",
			"machinery_type": mtype,
			"company": self.company,
			"rate": 500,
			"rate_unit": "Hour",
		}
		fields.update(kw)
		return frappe.get_doc(fields).insert(ignore_permissions=True)

	# --- create / mandatory / defaults --------------------------------------
	def test_create_machinery_with_mandatory_fields(self):
		m = self._machinery()
		self.assertEqual(m.company, self.company)
		self.assertTrue(m.machinery_type)

	def test_machinery_missing_mandatory_rejected(self):
		# company is also reqd=1, but on this single-company site Frappe's own
		# generic default resolution (tied to User Permissions) silently fills
		# it even when omitted — same discovery as the earlier CMP-001
		# investigation, so it can't be forced empty here to test the throw.
		mtype = self._machinery_type().name
		base = {
			"doctype": "Machinery",
			"machinery_name": "X",
			"machinery_type": mtype,
			"company": self.company,
		}
		for missing in ("machinery_name", "machinery_type"):
			fields = {k: v for k, v in base.items() if k != missing}
			with self.assertRaises(frappe.MandatoryError):
				frappe.get_doc(fields).insert(ignore_permissions=True)

	def test_ownership_and_status_default_to_first_option(self):
		# `ownership` and `status` are Select fields with no explicit default —
		# Frappe's own _set_defaults() auto-fills an unset Select field from its
		# first option ("Owned" / "Active") on insert, same discovery as
		# Construction Rate Master's `category` field earlier this session.
		m = self._machinery()
		self.assertEqual(m.ownership, "Owned")
		self.assertEqual(m.status, "Active")

	def test_owned_machinery_without_asset_link_still_saves(self):
		# `asset` only appears conditionally in the UI (depends_on) for Owned
		# machinery — it is not actually server-required (no mandatory_depends_on).
		m = self._machinery(ownership="Owned")
		self.assertFalse(m.asset)

	# --- update / delete -----------------------------------------------------
	def test_update_machinery_rate_persists(self):
		m = self._machinery(rate=500)
		m.rate = 750
		m.status = "Inactive"
		m.save(ignore_permissions=True)
		m.reload()
		self.assertEqual(m.rate, 750)
		self.assertEqual(m.status, "Inactive")

	def test_delete_machinery(self):
		m = self._machinery()
		frappe.delete_doc("Machinery", m.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Machinery", m.name))

	def test_delete_machinery_referenced_by_usage_is_link_protected(self):
		m = self._machinery()
		frappe.get_doc(
			{
				"doctype": "Machinery Usage",
				"machine": m.name,
				"date": "2026-07-30",
				"quantity": 2,
				"unit": "Hours",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Machinery", m.name, ignore_permissions=True)

	# --- register / dashboard -------------------------------------------------
	def test_dashboard_counts_machines_owned_hired(self):
		before = api.get_dashboard()
		self._machinery(ownership="Owned")
		self._machinery(ownership="Hired")
		after = api.get_dashboard()
		self.assertEqual(after["machines"], before["machines"] + 2)
		self.assertEqual(after["owned"], before["owned"] + 1)
		self.assertEqual(after["hired"], before["hired"] + 1)

	def test_dashboard_register_lists_machines(self):
		m = self._machinery()
		register = api.get_dashboard()["register"]
		row = next((r for r in register if r["name"] == m.name), None)
		self.assertIsNotNone(row)
		self.assertEqual(row["machinery_name"], m.machinery_name)
		self.assertEqual(row["ownership"], m.ownership)
		self.assertEqual(row["rate"], m.rate)

	def test_dashboard_equipment_cost_and_recent_usage(self):
		m = self._machinery(rate=500)
		before = api.get_dashboard()
		frappe.get_doc(
			{
				"doctype": "Machinery Usage",
				"machine": m.name,
				"date": "2026-07-30",
				"quantity": 3,
				"unit": "Hours",
				"fuel_cost": 200,
			}
		).insert(ignore_permissions=True)  # rate fetched from machine = 500

		after = api.get_dashboard()
		self.assertAlmostEqual(
			after["equipment_cost"], before["equipment_cost"] + (3 * 500 + 200), places=2
		)
		recent = after["recent_usage"]
		row = next((r for r in recent if r["machine"] == m.name), None)
		self.assertIsNotNone(row)
		self.assertAlmostEqual(row["total"], 3 * 500 + 200, places=2)
