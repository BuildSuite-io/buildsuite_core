# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Field Attendance -> BOQ Actual: submitting a sheet posts each coded row's wages through the
Labour / Overtime Attendance registers to its line and group; cancelling takes them off; uncoded
rows create registers but post nothing."""

import frappe

from buildsuite_core.api.boq_actuals import get_actuals_for_code, get_actuals_summary
from buildsuite_core.api.field_attendance import save_field_attendance
from buildsuite_core.tests import test_field_attendance as fa_tests
from buildsuite_core.tests import test_machinery_boq_actuals as boq_tests
from buildsuite_core.tests.base import BuildSuiteTestCase

ITEM = {"cost_code_type": "Item", "cost_code_group": "A", "cost_code_item": "A.01"}
GROUP = {"cost_code_type": "Group", "cost_code_group": "A"}


class TestFieldAttendanceBoqActuals(BuildSuiteTestCase):
	# Fixture builders are borrowed from the sibling suites without inheriting their tests.
	_project = fa_tests.TestFieldAttendance._project
	_worker = fa_tests.TestFieldAttendance._worker
	_estimate = boq_tests.TestMachineryBoqActuals._estimate

	def setUp(self):
		super().setUp()
		self.trade = f"Trade {frappe.generate_hash(length=4)}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": self.trade}).insert(ignore_permissions=True)
		self.project = self._project()
		self.worker_a = self._worker(900)
		self.worker_b = self._worker(1100)
		self.today = frappe.utils.today()
		self._estimate(self.project)

	def _sheet(self, rows, **header):
		res = save_field_attendance(
			project=self.project,
			date=self.today,
			status="Present",
			employee_list=frappe.as_json(rows),
			**header,
		)
		return frappe.get_doc("Field Attendance", res["name"])

	def _actual(self, code="A", item=False):
		bucket = get_actuals_summary(self.project)["by_item" if item else "by_group"]
		return (bucket.get(code) or {}).get("actual", 0)

	def test_submit_posts_exact_wages_and_cancel_reverses(self):
		sheet = self._sheet(
			[
				{"employee": self.worker_a, "status": "Present", "overtime_hours": 2, **ITEM},
				{"employee": self.worker_b, "status": "Half Day", **ITEM},
			]
		)
		self.assertEqual(self._actual(), 0)  # a draft posts nothing
		sheet.submit()
		# 900 + 2h x 50 overtime, plus half of 1100
		wages = 900 + 100 + 550
		self.assertEqual(self._actual(), wages)
		self.assertEqual(self._actual("A.01", item=True), wages)

		sheet.reload()
		sheet.cancel()
		self.assertEqual(self._actual(), 0)
		self.assertEqual(self._actual("A.01", item=True), 0)

	def test_absent_posts_nothing(self):
		sheet = self._sheet([{"employee": self.worker_a, "status": "Absent", **ITEM}])
		sheet.submit()
		self.assertEqual(self._actual(), 0)

	def test_registers_carry_the_row_code_and_a_row_can_differ(self):
		sheet = self._sheet(
			[
				{"employee": self.worker_a, "status": "Present", **ITEM},
				{"employee": self.worker_b, "status": "Present", **GROUP},
			]
		)
		sheet.submit()
		codes = {
			r.employee: (r.cost_code_type, r.cost_code_item)
			for r in frappe.get_all(
				"Labour Attendance Register",
				filters={"field_attendance": sheet.name},
				fields=["employee", "cost_code_type", "cost_code_item"],
			)
		}
		self.assertEqual(codes[self.worker_a], ("Item", "A.01"))
		self.assertEqual(codes[self.worker_b], ("Group", ""))
		self.assertEqual(self._actual(), 900 + 1100)
		self.assertEqual(self._actual("A.01", item=True), 900)

	def test_uncoded_rows_create_registers_but_do_not_post(self):
		sheet = self._sheet(
			[
				{"employee": self.worker_a, "status": "Present", **ITEM},
				{"employee": self.worker_b, "status": "Present", "overtime_hours": 1},
			]
		)
		res = save_field_attendance(
			name=sheet.name,
			project=self.project,
			date=self.today,
			employee_list=frappe.as_json(
				[
					{"employee": self.worker_a, "status": "Present", **ITEM},
					{"employee": self.worker_b, "status": "Present", "overtime_hours": 1},
				]
			),
		)
		self.assertEqual(res["unposted_cost"], 1100 + 50)
		sheet.reload()
		sheet.submit()
		self.assertEqual(
			frappe.db.count("Labour Attendance Register", {"field_attendance": sheet.name, "docstatus": 1}), 2
		)
		self.assertEqual(self._actual(), 900)

	def test_rejects_a_code_outside_the_estimate(self):
		with self.assertRaisesRegex(frappe.ValidationError, "not in the approved estimate"):
			self._sheet(
				[
					{
						"employee": self.worker_a,
						"status": "Present",
						"cost_code_type": "Item",
						"cost_code_group": "Z",
						"cost_code_item": "Z.99",
					}
				]
			)

	def test_amended_sheet_posts_again(self):
		sheet = self._sheet([{"employee": self.worker_a, "status": "Present", **ITEM}])
		sheet.submit()
		sheet.reload()
		sheet.cancel()
		amended = frappe.copy_doc(sheet)
		amended.amended_from = sheet.name
		amended.docstatus = 0
		amended.insert()
		amended.submit()
		self.assertEqual(self._actual(), 900)

	def test_breakdown_lists_registers_linked_to_the_sheet(self):
		sheet = self._sheet([{"employee": self.worker_a, "status": "Present", "overtime_hours": 1, **ITEM}])
		sheet.submit()
		log = get_actuals_for_code(self.project, group_code="A")
		entries = [
			e
			for e in log["entries"]
			if e["source_doctype"] in ("Labour Attendance Register", "Overtime Attendance Register")
		]
		self.assertEqual(sorted(e["kind"] for e in entries), ["Full Day", "Overtime"])
		self.assertTrue(all(e["field_attendance"] == sheet.name for e in entries))
