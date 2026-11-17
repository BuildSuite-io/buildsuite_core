# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The sales permissions reach existing sites additively (permissions.setup
.grant_missing_sales_permissions, run by patches/setup_lead_permissions): a role gets a default
rule only where it has none, a site's own edits are never reset, and nothing is deleted."""

import frappe

from buildsuite_core.permissions.setup import (
	QUOTATION_ROLE_PERMS,
	SALES_REPORTS,
	grant_missing_sales_permissions,
)
from buildsuite_core.tests.base import BuildSuiteTestCase

ROLE = "BuildSuite Estimator"


def _rule(doctype, role):
	return frappe.db.get_value(
		"Custom DocPerm",
		{"parent": doctype, "role": role, "permlevel": 0},
		["name", "read", "write", "submit", "delete"],
		as_dict=True,
	)


class TestSalesPermissionsPatch(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.clear_cache)

	def test_a_missing_rule_is_added_with_the_default(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Quotation", "role": ROLE})
		grant_missing_sales_permissions()
		rule = _rule("Quotation", ROLE)
		self.assertTrue(rule, "the estimator's Quotation rule was not added")
		self.assertEqual(rule.submit, QUOTATION_ROLE_PERMS[ROLE].get("submit", 0))

	def test_a_sites_own_edit_is_left_alone(self):
		grant_missing_sales_permissions()
		rule = _rule("Quotation", ROLE)
		# The site's admin narrowed the estimator to read-only in Role Permission Manager.
		frappe.db.set_value("Custom DocPerm", rule.name, {"write": 0, "submit": 0, "delete": 0})
		grant_missing_sales_permissions()
		self.assertEqual(_rule("Quotation", ROLE), {**rule, "write": 0, "submit": 0, "delete": 0})

	def test_nothing_is_deleted(self):
		grant_missing_sales_permissions()
		# A role outside the sales table that a site gave Quotation access to.
		frappe.permissions.add_permission("Quotation", "BuildSuite Accountant", 0)
		before = frappe.db.count("Custom DocPerm", {"parent": "Quotation"})
		grant_missing_sales_permissions()
		self.assertEqual(frappe.db.count("Custom DocPerm", {"parent": "Quotation"}), before)
		self.assertTrue(_rule("Quotation", "BuildSuite Accountant"))

	def test_the_report_only_gains_roles_that_can_see_its_tile(self):
		from buildsuite_core.report_access import _grantable_roles

		for report in SALES_REPORTS:
			if frappe.db.exists("Report", report):
				# Start from no BuildSuite roles on the report (this test's own transaction).
				frappe.db.delete(
					"Has Role", {"parenttype": "Report", "parent": report, "role": ["like", "BuildSuite%"]}
				)
		grant_missing_sales_permissions()
		for report in SALES_REPORTS:
			if not frappe.db.exists("Report", report):
				continue
			grantable, constrained, _slugs = _grantable_roles(report)
			roles = {r.role for r in frappe.get_doc("Report", report).roles}
			if constrained:
				extra = {r for r in roles if r.startswith("BuildSuite") and r not in grantable}
				self.assertFalse(extra, f"{report} granted to roles that can't see its tile: {extra}")
