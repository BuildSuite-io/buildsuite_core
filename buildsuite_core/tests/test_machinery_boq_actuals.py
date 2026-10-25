# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Machinery Usage -> BOQ Actual: a coded log posts quantity x rate + fuel to its line and group
as soon as it is saved; editing updates it and deleting removes it. Uncoded logs post nothing."""

import frappe

from buildsuite_core.api import boq as boq_api
from buildsuite_core.api.boq_actuals import get_actuals_summary
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestMachineryBoqActuals(BuildSuiteTestCase):
	def _project(self):
		h = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {h}",
				"custom_project_id": f"UAT-{h}",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

	def _estimate(self, project):
		boq = frappe.get_doc(
			{"doctype": "BOQ", "project": project, "title": "UAT", "margin_rate": 0, "tax_rate": 0}
		).insert(ignore_permissions=True)
		group = frappe.get_doc(
			{"doctype": "BOQ Group", "boq": boq.name, "code": "A", "group_name": "Civil"}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": boq.name,
				"boq_group": group.name,
				"code": "A.01",
				"description": "Excavation",
				"unit": "Nos",
				"planned_qty": 1,
				"rate": 100,
			}
		).insert(ignore_permissions=True)
		boq_api.approve_boq(boq.name)

	def _machine(self, rate=3000):
		mtype = frappe.get_doc(
			{"doctype": "Machinery Type", "type_name": f"UAT Type {frappe.generate_hash(length=5)}"}
		).insert(ignore_permissions=True)
		return frappe.get_doc(
			{
				"doctype": "Machinery",
				"machinery_name": f"UAT Machine {frappe.generate_hash(length=5)}",
				"machinery_type": mtype.name,
				"company": self.company,
				"rate": rate,
				"rate_unit": "Day",
			}
		).insert(ignore_permissions=True)

	def _usage(self, project, machine, **kw):
		doc = {
			"doctype": "Machinery Usage",
			"machine": machine.name,
			"project": project,
			"date": "2026-07-30",
			"quantity": 2,
			"unit": "Days",
			"fuel_cost": 1500,
		}
		doc.update(kw)
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def _actual(self, project, code="A", item=False):
		s = get_actuals_summary(project)
		bucket = s["by_item"] if item else s["by_group"]
		return (bucket.get(code) or {}).get("actual", 0)

	def test_coded_log_posts_edits_and_deletes(self):
		p = self._project()
		self._estimate(p.name)
		m = self._machine()
		log = self._usage(p.name, m, cost_code_type="Item", cost_code_group="A", cost_code_item="A.01")
		self.assertEqual(log.cost_code_group, "A")
		self.assertEqual(self._actual(p.name), 2 * 3000 + 1500)
		self.assertEqual(self._actual(p.name, "A.01", item=True), 7500)

		log.quantity = 3
		log.save(ignore_permissions=True)
		self.assertEqual(self._actual(p.name), 3 * 3000 + 1500)

		frappe.delete_doc("Machinery Usage", log.name, ignore_permissions=True)
		self.assertEqual(self._actual(p.name), 0)

	def test_group_code_and_uncoded_and_task_only(self):
		p = self._project()
		self._estimate(p.name)
		m = self._machine()
		self._usage(p.name, m, cost_code_type="Group", cost_code_group="A")
		self.assertEqual(self._actual(p.name), 7500)
		self._usage(p.name, m)  # uncoded
		self._usage(p.name, m, task=self._make_task(p.name).name)  # legacy task-only
		self.assertEqual(self._actual(p.name), 7500)

	def test_foreign_cost_code_rejected(self):
		p = self._project()
		self._estimate(p.name)
		other = self._project()
		with self.assertRaises(frappe.ValidationError):
			self._usage(other.name, self._machine(), cost_code_type="Group", cost_code_group="A")

	def test_project_change_clears_cost_code(self):
		p = self._project()
		self._estimate(p.name)
		other = self._project()
		log = self._usage(p.name, self._machine(), cost_code_type="Group", cost_code_group="A")
		log.project = other.name
		log.save(ignore_permissions=True)
		self.assertFalse(log.cost_code_group)
		self.assertEqual(self._actual(p.name), 0)
