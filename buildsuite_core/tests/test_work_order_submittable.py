# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Subcontractor Work Order is natively submittable: Draft → Submitted → Cancelled + Amend.
Only Submitted WOs count as committed cost; cancelling is blocked once measurements/bills exist."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestWorkOrderSubmittable(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _subcontractor(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": f"Sub {self._n}",
					"supplier_type": "Subcontractor",
					"supplier_group": "Subcontractor",
					"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _wo(self, cost_code_group="G1", qty=10, rate=100):
		from buildsuite_core.api.subcontract import save_work_order

		return save_work_order(
			subcontractor=self._subcontractor(),
			project=self.project,
			date="2026-07-20",
			retention_percent=5,
			lines=frappe.as_json(
				[
					{
						"scope": "Work",
						"cost_code_type": "Group",
						"cost_code_group": cost_code_group,
						"uom": "Nos",
						"qty": qty,
						"rate": rate,
					}
				]
			),
		)["name"]

	def test_submit_makes_it_committed(self):
		"""A draft WO is not committed cost; submitting it makes its lines count toward the BOQ
		committed column, grouped by cost code."""
		from buildsuite_core.api.subcontract import committed_by_cost_code, get_work_order, submit_work_order

		name = self._wo(cost_code_group="G1", qty=10, rate=100)  # 1000
		self.assertEqual(get_work_order(name)["status"], "Draft")
		self.assertEqual(committed_by_cost_code(self.project).get("G1", 0), 0)

		submit_work_order(name)
		self.assertEqual(frappe.db.get_value("Subcontractor Work Order", name, "docstatus"), 1)
		data = get_work_order(name)
		self.assertEqual(data["status"], "Submitted")
		self.assertEqual(data["actions"], ["record_measurement", "bill_progress", "cancel"])
		self.assertAlmostEqual(committed_by_cost_code(self.project).get("G1"), 1000, places=2)

	def test_cancel_blocked_when_measurement_book_exists(self):
		from buildsuite_core.api.subcontract import cancel_work_order, submit_work_order

		name = self._wo()
		submit_work_order(name)
		wo = frappe.get_doc("Subcontractor Work Order", name)
		frappe.get_doc(
			{
				"doctype": "Measurement Book",
				"work_order": name,
				"project": self.project,
				"date": "2026-07-21",
				"entries": [
					{
						"description": "m",
						"work_order_line": wo.lines[0].name,
						"quantity": 5,
						"is_deduction": 0,
					}
				],
			}
		).insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, cancel_work_order, name)

	def test_amend_clones_to_a_new_draft(self):
		from buildsuite_core.api.subcontract import amend_work_order, cancel_work_order, submit_work_order

		name = self._wo()
		submit_work_order(name)
		cancel_work_order(name)  # no MBs/bills → cancels
		amended = amend_work_order(name)
		self.assertEqual(amended["status"], "Draft")
		self.assertEqual(amended["amended_from"], name)
		self.assertNotEqual(amended["name"], name)
