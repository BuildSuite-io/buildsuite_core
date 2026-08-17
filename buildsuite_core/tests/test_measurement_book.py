# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Measurement Book records what was measured on site between the Work Order and the Bill.
Quantity derives from nos x L x B x D (or is typed directly); deduction rows subtract. Only
Certified books feed measured-to-date and are locked from editing until reverted to Draft."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestMeasurementBook(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _submitted_wo(self):
		from buildsuite_core.api.subcontract import save_work_order, submit_work_order

		sub = (
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
		name = save_work_order(
			subcontractor=sub,
			project=self.project,
			date="2026-07-20",
			retention_percent=5,
			lines=frappe.as_json([{"scope": "Tiling", "uom": "Nos", "qty": 100, "rate": 85}]),
		)["name"]
		submit_work_order(name)
		wo = frappe.get_doc("Subcontractor Work Order", name)
		return wo.name, wo.lines[0].name

	def _mb(self, wo, line, entries):
		from buildsuite_core.api.subcontract import save_measurement_book

		return save_measurement_book(
			work_order=wo, project=self.project, date="2026-07-21", entries=frappe.as_json(entries)
		)["name"]

	def test_quantity_derived_and_deduction_signed(self):
		"""nos x L x B x D fills quantity when not given; a deduction row subtracts from the total."""
		wo, line = self._submitted_wo()
		name = self._mb(
			wo,
			line,
			[
				{
					"description": "Slab",
					"work_order_line": line,
					"nos": 2,
					"length": 3,
					"breadth": 4,
					"depth": 1,
				},
				{"description": "Cutout", "work_order_line": line, "quantity": 4, "is_deduction": 1},
			],
		)
		mb = frappe.get_doc("Measurement Book", name)
		self.assertAlmostEqual(mb.entries[0].quantity, 24, places=2)  # 2*3*4*1
		self.assertAlmostEqual(mb.measured_total, 20, places=2)  # 24 - 4

	def test_certify_feeds_measured_and_locks_editing(self):
		from buildsuite_core.api.subcontract import (
			certify_measurement_book,
			get_wo_measurements,
			save_measurement_book,
		)

		wo, line = self._submitted_wo()
		name = self._mb(wo, line, [{"description": "m", "work_order_line": line, "quantity": 30}])
		# a Draft MB does not feed measured-to-date
		self.assertEqual(get_wo_measurements(wo)["measured_by_line"].get(line, 0), 0)

		certify_measurement_book(name)
		self.assertAlmostEqual(get_wo_measurements(wo)["measured_by_line"].get(line), 30, places=2)
		# a Certified book is locked from editing
		self.assertRaises(
			frappe.ValidationError,
			save_measurement_book,
			name=name,
			work_order=wo,
			project=self.project,
			date="2026-07-21",
			entries=frappe.as_json([{"description": "m", "work_order_line": line, "quantity": 99}]),
		)

	def test_revert_reopens_for_editing(self):
		from buildsuite_core.api.subcontract import (
			certify_measurement_book,
			get_wo_measurements,
			revert_measurement_book,
			save_measurement_book,
		)

		wo, line = self._submitted_wo()
		name = self._mb(wo, line, [{"description": "m", "work_order_line": line, "quantity": 30}])
		certify_measurement_book(name)
		revert_measurement_book(name)
		# reverted → no longer feeds measured-to-date, and editable again
		self.assertEqual(get_wo_measurements(wo)["measured_by_line"].get(line, 0), 0)
		save_measurement_book(
			name=name,
			work_order=wo,
			project=self.project,
			date="2026-07-21",
			entries=frappe.as_json([{"description": "m", "work_order_line": line, "quantity": 40}]),
		)
		self.assertAlmostEqual(frappe.get_doc("Measurement Book", name).measured_total, 40, places=2)

	def test_project_defaults_from_work_order(self):
		# Creating an MB with work_order set but no project auto-fills the
		# project from the Work Order.
		from buildsuite_core.api.subcontract import save_measurement_book

		wo, line = self._submitted_wo()
		out = save_measurement_book(
			work_order=wo,
			date="2026-07-21",
			entries=frappe.as_json([{"description": "m", "work_order_line": line, "quantity": 10}]),
		)
		self.assertEqual(out["project"], self.project)

	def test_company_anchored_to_project(self):
		wo, line = self._submitted_wo()
		name = self._mb(wo, line, [{"description": "m", "work_order_line": line, "quantity": 10}])
		mb = frappe.get_doc("Measurement Book", name)
		self.assertEqual(mb.company, self.company)

	def test_new_measurement_book_starts_draft(self):
		wo, line = self._submitted_wo()
		name = self._mb(wo, line, [{"description": "m", "work_order_line": line, "quantity": 10}])
		mb = frappe.get_doc("Measurement Book", name)
		self.assertEqual(mb.status, "Draft")

	def test_certify_is_idempotent(self):
		from buildsuite_core.api.subcontract import certify_measurement_book

		wo, line = self._submitted_wo()
		name = self._mb(wo, line, [{"description": "m", "work_order_line": line, "quantity": 10}])
		certify_measurement_book(name)
		certifier_first = frappe.db.get_value("Measurement Book", name, "certified_by")

		out = certify_measurement_book(name)  # already Certified — must be a safe no-op
		self.assertEqual(out["status"], "Certified")
		self.assertEqual(frappe.db.get_value("Measurement Book", name, "certified_by"), certifier_first)

	def test_measured_by_line_sums_across_multiple_certified_books(self):
		# Progressive/partial billing: two SEPARATE certified books against the
		# same SOV line accumulate rather than overwrite each other.
		from buildsuite_core.api.subcontract import certify_measurement_book, get_wo_measurements

		wo, line = self._submitted_wo()
		mb1 = self._mb(wo, line, [{"description": "m1", "work_order_line": line, "quantity": 30}])
		certify_measurement_book(mb1)
		mb2 = self._mb(wo, line, [{"description": "m2", "work_order_line": line, "quantity": 20}])
		certify_measurement_book(mb2)

		self.assertAlmostEqual(get_wo_measurements(wo)["measured_by_line"].get(line), 50, places=2)

	def test_get_work_order_lines_returns_sov_lines_for_picker(self):
		from buildsuite_core.api.subcontract import get_work_order_lines

		wo, line = self._submitted_wo()
		lines = get_work_order_lines(wo)
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0]["name"], line)
		self.assertEqual(lines[0]["scope"], "Tiling")

	def test_delete_measurement_book(self):
		wo, line = self._submitted_wo()
		name = self._mb(wo, line, [{"description": "m", "work_order_line": line, "quantity": 10}])
		frappe.delete_doc("Measurement Book", name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Measurement Book", name))
