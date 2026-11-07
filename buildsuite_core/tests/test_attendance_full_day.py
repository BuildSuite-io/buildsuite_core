# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Field Attendance sheets and their registers carry the full day they were made with."""

import frappe

from buildsuite_core.api.field_attendance import save_field_attendance
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestAttendanceFullDay(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.trade = f"Trade {self._n}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": self.trade}).insert(ignore_permissions=True)
		self.project = self._make_project().name
		self.company = frappe.db.get_value("Project", self.project, "company")
		frappe.db.set_value("Company", self.company, "full_day_hours", 9)
		self.today = frappe.utils.today()
		self.worker_a = self._worker(900)
		self.worker_b = self._worker(1100)

	def _worker(self, wage):
		return (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"naming_series": "HR-EMP-",
					"first_name": f"FD {frappe.generate_hash(length=4)}",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"company": self.company,
					"is_labour": 1,
					"custom_trade": self.trade,
					"custom_wage": wage,
					"custom_wage_for_overtime": 50,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _sheet(self, rows, date=None):
		return save_field_attendance(
			project=self.project,
			date=date or self.today,
			status="Present",
			employee_list=frappe.as_json(rows),
		)

	def _submit(self, res):
		frappe.get_doc("Field Attendance", res["name"]).submit()
		return res["name"]

	def _labour(self, sheet, employee):
		return frappe.db.get_value(
			"Labour Attendance Register",
			{"field_attendance": sheet, "employee": employee, "docstatus": 1},
			["full_day_hours", "regular_hours", "source", "status", "daily_wage_calculated", "wage_rate"],
			as_dict=True,
		)

	# --- the sheet's own day ---------------------------------------------
	def test_a_draft_follows_the_settings_and_a_submitted_sheet_does_not(self):
		res = self._sheet([{"employee": self.worker_a, "status": "Present"}])
		self.assertEqual(frappe.db.get_value("Field Attendance", res["name"], "full_day_hours"), 9)

		# still a draft: a company change is picked up on the next save
		frappe.db.set_value("Company", self.company, "full_day_hours", 10)
		doc = frappe.get_doc("Field Attendance", res["name"])
		doc.save()
		self.assertEqual(doc.full_day_hours, 10)

		# submitted sheet keeps the day it was submitted on
		frappe.db.set_value("Company", self.company, "full_day_hours", 9)
		sheet = self._submit(res)
		self.assertEqual(frappe.db.get_value("Field Attendance", sheet, "full_day_hours"), 9)

	def test_sheet_and_register_rows_stay_9_after_the_company_changes_to_10(self):
		res = self._sheet(
			[
				{"employee": self.worker_a, "status": "Present", "overtime_hours": 2},
				{"employee": self.worker_b, "status": "Half Day"},
			]
		)
		sheet = self._submit(res)
		frappe.db.set_value("Company", self.company, "full_day_hours", 10)

		self.assertEqual(frappe.db.get_value("Field Attendance", sheet, "full_day_hours"), 9)
		a, b = self._labour(sheet, self.worker_a), self._labour(sheet, self.worker_b)
		self.assertEqual((a.full_day_hours, a.regular_hours, a.source), (9, 9, "Attendance"))
		self.assertEqual((b.full_day_hours, b.regular_hours), (9, 4.5))
		ot = frappe.db.get_value(
			"Overtime Attendance Register",
			{"field_attendance": sheet, "employee": self.worker_a, "docstatus": 1},
			["full_day_hours", "source"],
			as_dict=True,
		)
		self.assertEqual((ot.full_day_hours, ot.source), (9, "Attendance"))

	# --- hours vs wages ---------------------------------------------------
	def test_ten_hour_project_present_and_half_day(self):
		frappe.db.set_value("Project", self.project, "full_day_hours", 10)
		res = self._sheet(
			[
				{"employee": self.worker_a, "status": "Present"},
				{"employee": self.worker_b, "status": "Half Day"},
			]
		)
		sheet = self._submit(res)
		a, b = self._labour(sheet, self.worker_a), self._labour(sheet, self.worker_b)

		# Present: 10 regular hours = 1 man-day, at one day's wage
		self.assertEqual((a.full_day_hours, a.regular_hours), (10, 10))
		self.assertEqual(a.regular_hours / a.full_day_hours, 1)
		self.assertEqual(a.daily_wage_calculated, 900)
		# Half Day: 5 hours = 0.5 man-day, at half a day's wage
		self.assertEqual((b.full_day_hours, b.regular_hours), (10, 5))
		self.assertEqual(b.regular_hours / b.full_day_hours, 0.5)
		self.assertEqual(b.daily_wage_calculated, 1100 / 2)

	def test_absent_has_no_hours_and_no_wage(self):
		res = self._sheet([{"employee": self.worker_a, "status": "Absent"}])
		sheet = self._submit(res)
		a = self._labour(sheet, self.worker_a)
		self.assertEqual((a.regular_hours, a.daily_wage_calculated, a.status), (0, 0, "Absent"))

	# --- 24-hour check ----------------------------------------------------
	def test_a_day_over_24_hours_is_refused_on_submit(self):
		# 9 regular + 10 overtime on one sheet = 19
		first = self._submit(
			self._sheet([{"employee": self.worker_a, "status": "Present", "overtime_hours": 10}])
		)
		self.assertTrue(first)
		# another sheet adds 6 more overtime on the same day -> 9 + 10 + 6 = 25 > 24
		second = self._sheet([{"employee": self.worker_a, "status": "Overtime Only", "overtime_hours": 6}])
		with self.assertRaisesRegex(frappe.ValidationError, "more than 24 hours"):
			frappe.get_doc("Field Attendance", second["name"]).submit()

	def test_a_day_up_to_24_hours_is_accepted(self):
		self._submit(self._sheet([{"employee": self.worker_a, "status": "Present", "overtime_hours": 10}]))
		# 9 + 10 + 5 = 24 exactly
		second = self._sheet([{"employee": self.worker_a, "status": "Overtime Only", "overtime_hours": 5}])
		frappe.get_doc("Field Attendance", second["name"]).submit()

	# --- the patch for existing data -------------------------------------
	def test_patch_gives_existing_rows_an_8_hour_day(self):
		from buildsuite_core.patches.set_attendance_full_day_hours import execute

		res = self._sheet(
			[
				{"employee": self.worker_a, "status": "Present", "overtime_hours": 1},
				{"employee": self.worker_b, "status": "Half Day"},
			]
		)
		sheet = self._submit(res)
		# make them look like rows from before the feature
		frappe.db.sql("UPDATE `tabField Attendance` SET full_day_hours = 0 WHERE name = %s", sheet)
		for dt in ("Labour Attendance Register", "Overtime Attendance Register"):
			frappe.db.sql(
				f"UPDATE `tab{dt}` SET full_day_hours = 0, source = NULL WHERE field_attendance = %s", sheet
			)
		frappe.db.sql(
			"UPDATE `tabLabour Attendance Register` SET regular_hours = 0 WHERE field_attendance = %s", sheet
		)

		execute()

		self.assertEqual(frappe.db.get_value("Field Attendance", sheet, "full_day_hours"), 8)
		a, b = self._labour(sheet, self.worker_a), self._labour(sheet, self.worker_b)
		self.assertEqual((a.full_day_hours, a.regular_hours, a.source), (8, 8, "Attendance"))
		self.assertEqual((b.full_day_hours, b.regular_hours, b.source), (8, 4, "Attendance"))
		ot = frappe.db.get_value(
			"Overtime Attendance Register",
			{"field_attendance": sheet},
			["full_day_hours", "source"],
			as_dict=True,
		)
		self.assertEqual((ot.full_day_hours, ot.source), (8, "Attendance"))
