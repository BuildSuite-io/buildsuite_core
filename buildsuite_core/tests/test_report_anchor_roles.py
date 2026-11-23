# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The bespoke reports' Report anchors carry their persona roles on a fresh site too.

On a new site seed_report_anchors used to run before the BuildSuite roles existed, so every anchor
was created with the admin roles only and no persona could open a Procurement (or Finance /
Workforce) report. setup_record_permissions now gives them their roles once the roles exist, and a
patch repairs sites created with the bug."""

import frappe

from buildsuite_core.patches import give_report_anchors_their_roles as patch_mod
from buildsuite_core.report_access import _ADMIN_ROLES, _matrix_roles
from buildsuite_core.tests.base import BuildSuiteTestCase

PURCHASE_REGISTER = "BuildSuite Purchase Register"
COMPARISON = "BuildSuite Supplier Quotation Comparison"


def _roles(report):
	return {r.role for r in frappe.get_doc("Report", report).roles}


def _set_roles(report, roles):
	doc = frappe.get_doc("Report", report)
	doc.set("roles", [{"role": r} for r in roles])
	doc.flags.ignore_permissions = True
	doc.save()


class TestReportAnchorRoles(BuildSuiteTestCase):
	def test_every_procurement_anchor_carries_the_procurement_officer(self):
		for report, roles in _matrix_roles().items():
			if "BuildSuite Procurement Officer" in roles and frappe.db.exists("Report", report):
				with self.subTest(report=report):
					self.assertIn("BuildSuite Procurement Officer", _roles(report))

	def test_patch_gives_an_admin_only_anchor_its_persona_roles(self):
		"""The fresh-site state: admin roles only. The patch adds the matrix's persona roles."""
		for report in (PURCHASE_REGISTER, COMPARISON):
			_set_roles(report, [r for r in _ADMIN_ROLES if frappe.db.exists("Role", r)])
		patch_mod.execute()
		for report in (PURCHASE_REGISTER, COMPARISON):
			with self.subTest(report=report):
				self.assertEqual(_roles(report), set(_matrix_roles()[report]))

	def test_patch_leaves_an_anchor_an_admin_has_given_roles(self):
		"""Any persona role on an anchor is someone's choice: nothing is added or removed."""
		chosen = {"BuildSuite Director", "System Manager"}
		_set_roles(PURCHASE_REGISTER, chosen)
		patch_mod.execute()
		self.assertEqual(_roles(PURCHASE_REGISTER), chosen)
