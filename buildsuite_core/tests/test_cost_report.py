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

	# --- Journal Entry (JV) actuals rail -----------------------------------------------------
	def _account(self, root_type, account_type=None):
		filters = {"company": self.company, "root_type": root_type, "is_group": 0}
		if account_type:
			filters["account_type"] = account_type
		names = frappe.get_all("Account", filters=filters, limit=1, pluck="name")
		return names[0] if names else None

	def test_journal_entry_actual_by_cost_code(self):
		"""A submitted JV expense line charged to a cost code books its debit into BOQ actual
		(Overhead), and cancelling reverses it — same derived-getter behaviour as the other rails."""
		from buildsuite_core.api.boq_actuals import get_actuals_summary

		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name, code="A", name="Civil")
		self._item(b.name, g.name, qty=10, rate=100, cost_head="Material")
		boq_api.approve_boq(b.name)

		expense_account = self._account("Expense")
		cash_account = self._account("Asset", "Cash") or self._account("Asset")
		cost_center = frappe.db.get_value("Company", self.company, "cost_center")

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.posting_date = "2026-07-20"
		je.append(
			"accounts",
			{
				"account": expense_account,
				"debit_in_account_currency": 5000,
				"cost_center": cost_center,
				"project": p.name,
				"custom_cost_code_type": "Group",
				"custom_cost_code_group": "A",
				"custom_cost_code_label": "A · Civil",
			},
		)
		je.append(
			"accounts",
			{"account": cash_account, "credit_in_account_currency": 5000, "cost_center": cost_center},
		)
		je.flags.ignore_permissions = True
		je.insert()

		# Draft JV contributes nothing (reads only submitted docs).
		self.assertEqual(get_actuals_summary(p.name)["by_group"].get("A", {}).get("actual", 0), 0)

		je.submit()
		summary = get_actuals_summary(p.name)
		self.assertAlmostEqual(summary["by_group"]["A"]["actual"], 5000, places=2)
		self.assertAlmostEqual(summary["by_group"]["A"]["by_cost_type"]["Overhead"], 5000, places=2)

		# The drill-down entry references the JV (its "BOQ actual hyperlink").
		from buildsuite_core.api.boq_actuals import get_actuals_for_code

		entries = get_actuals_for_code(p.name, group_code="A")["entries"]
		je_entry = next(e for e in entries if e["source_doctype"] == "Journal Entry")
		self.assertEqual(je_entry["source_name"], je.name)

		# Cancelling reverses the contribution.
		je.cancel()
		self.assertEqual(get_actuals_summary(p.name)["by_group"].get("A", {}).get("actual", 0), 0)
