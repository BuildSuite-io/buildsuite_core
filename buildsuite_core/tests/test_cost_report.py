# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Cost vs Budget by Cost Code — Planned aggregation per cost code, dominant-cost-type grouping,
variance, and the Approved-BOQ gate. Committed/Actual are covered by the subcontract + boq_actuals
suites; here they are 0 (no work orders / bills), so variance = −planned."""

import frappe

from buildsuite_core.api import boq as boq_api
from buildsuite_core.api.cost_report import cost_vs_budget_by_cost_code
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestCostVsBudget(BuildSuiteTestCase):
	def _boq(self, project):
		return frappe.get_doc(
			{"doctype": "BOQ", "project": project, "title": "UAT BOQ", "margin_rate": 0, "tax_rate": 0}
		).insert(ignore_permissions=True)

	def _group(self, boq, code="A", name="Civil"):
		return frappe.get_doc(
			{"doctype": "BOQ Group", "boq": boq, "code": code, "group_name": name}
		).insert(ignore_permissions=True)

	def _item(self, boq, group, qty, rate, code=None, cost_head=None):
		return frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": boq,
				"boq_group": group,
				"code": code or f"A.{frappe.generate_hash(length=3)}",
				"description": "x",
				"unit": "Nos",
				"planned_qty": qty,
				"rate": rate,
				"cost_head": cost_head,
			}
		).insert(ignore_permissions=True)

	def test_no_project_returns_empty(self):
		res = cost_vs_budget_by_cost_code("")
		self.assertIsNone(res["boq"])
		self.assertEqual(res["rows"], [])

	def test_draft_boq_is_not_measured(self):
		# Only Approved BOQs count — a Draft revision must never be costed against.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)  # left Draft
		self._item(b.name, self._group(b.name).name, qty=10, rate=100, cost_head="Labour")
		res = cost_vs_budget_by_cost_code(p.name)
		self.assertIsNone(res["boq"])
		self.assertEqual(res["rows"], [])

	def test_planned_dominant_cost_type_and_variance(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name, code="A", name="Civil")
		# Labour (1000) dominates Material (200) → the group's cost type is Labour.
		labour = self._item(b.name, g.name, qty=10, rate=100, cost_head="Labour")
		material = self._item(b.name, g.name, qty=2, rate=100, cost_head="Material")
		boq_api.approve_boq(b.name)

		expected_planned = frappe.db.get_value(
			"BOQ Item", labour.name, "planned_amount"
		) + frappe.db.get_value("BOQ Item", material.name, "planned_amount")

		res = cost_vs_budget_by_cost_code(p.name)
		self.assertEqual(res["boq"], b.name)
		self.assertEqual(len(res["rows"]), 1)

		row = res["rows"][0]
		self.assertEqual(row["code"], "A")
		self.assertEqual(row["name"], "Civil")
		self.assertEqual(row["costType"], "Labour")
		self.assertEqual(row["planned"], expected_planned)
		self.assertEqual(row["committed"], 0)
		self.assertEqual(row["actual"], 0)
		# No commitments/actuals yet, so the whole budget is unspent: variance = actual − planned.
		self.assertEqual(row["variance"], -expected_planned)
		self.assertAlmostEqual(row["variancePct"], -100.0)

	def test_unclassified_when_no_cost_head(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name, code="B", name="MEP")
		self._item(b.name, g.name, qty=5, rate=50)  # no cost_head
		boq_api.approve_boq(b.name)

		res = cost_vs_budget_by_cost_code(p.name)
		self.assertEqual(len(res["rows"]), 1)
		self.assertEqual(res["rows"][0]["costType"], "Unclassified")
