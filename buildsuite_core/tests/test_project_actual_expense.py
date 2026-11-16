# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project page: Actual vs Planned reads the project's expense from the posted ledger
(api/finance_report.project_actual_expense), so a posted Subcontractor Bill shows as actual
even with no Approved BOQ or cost code, and reconciles with the Project Finance P&L."""

import frappe
from frappe.utils import flt

from buildsuite_core.api.finance_report import profit_and_loss, project_actual_expense
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestProjectActualExpense(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _submitted_subcontractor_bill(self, amount=100000):
		sub = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"Sub {frappe.generate_hash(length=6)}",
				"supplier_type": "Subcontractor",
				"supplier_group": "Subcontractor",
				"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
			}
		).insert(ignore_permissions=True)
		bill = frappe.get_doc(
			{
				"doctype": "Subcontractor Bill",
				"is_direct": 1,
				"subcontractor": sub.name,
				"project": self.project,
				"company": self.company,
				"date": "2026-07-20",
				"retention_percent": 10,
				"lines": [{"scope": "Site clearance", "this_period_amount": amount}],
			}
		)
		bill.insert(ignore_permissions=True)
		bill.submit()
		return bill

	def test_no_postings_is_zero(self):
		self.assertEqual(project_actual_expense(self.project)["actual"], 0)

	def test_posted_subcontractor_bill_counts_and_matches_pnl(self):
		self._submitted_subcontractor_bill(100000)
		actual = project_actual_expense(self.project)["actual"]
		self.assertGreater(actual, 0)
		self.assertAlmostEqual(
			flt(actual), flt(profit_and_loss(project=self.project)["totals"]["expense"]), places=2
		)

	def test_other_projects_are_excluded(self):
		self._submitted_subcontractor_bill(100000)
		self._n = frappe.generate_hash(length=6)  # the builder derives the project id from _n
		other = self._make_project(company=self.company).name
		self.assertEqual(project_actual_expense(other)["actual"], 0)
