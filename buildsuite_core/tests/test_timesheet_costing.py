# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Timesheets: cost code, costing on the project's full day, the one-day rule and the import plan."""

from unittest.mock import patch

import frappe

from buildsuite_core.api import timesheet as api
from buildsuite_core.api.field_employee import ensure_labour_employment_type
from buildsuite_core.tests.base import BuildSuiteTestCase

CODES = [
	{"type": "Group", "group_code": "B", "item_code": "", "label": "B · Joinery"},
	{"type": "Item", "group_code": "B", "item_code": "B.04", "label": "B.04 · Wardrobes"},
]


class TestTimesheetCosting(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		trade = f"Trade {self._n}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": trade}).insert(ignore_permissions=True)
		self.project = self._make_project().name
		self.company = frappe.db.get_value("Project", self.project, "company")
		frappe.db.set_value("Project", self.project, "full_day_hours", 9)
		self.worker = self._worker(trade, 750, 50)
		self.day = frappe.utils.today()

	def _worker(self, trade, wage, ot):
		return (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"naming_series": "HR-EMP-",
					"first_name": f"Rajesh {frappe.generate_hash(length=4)}",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"company": self.company,
					"is_labour": 1,
					# is_labour follows the employment type, so a field worker carries "Labour"
					"employment_type": ensure_labour_employment_type(),
					"custom_trade": trade,
					"custom_wage": wage,
					"custom_wage_for_overtime": ot,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _save(self, rows, **kw):
		return api.save_timesheet(
			employee=kw.pop("employee", self.worker),
			date=kw.pop("date", self.day),
			time_logs=frappe.as_json(rows),
			**kw,
		)

	# --- costing -----------------------------------------------------------
	def test_six_hours_on_a_nine_hour_project(self):
		ts = self._save([{"project": self.project, "hours": 6}])
		row = ts["rows"][0]
		# 750 a day / 9 h = 83.33 an hour (was 93.75 on an 8-hour day); 6 h = 499.98
		self.assertEqual(
			(row["full_day_hours"], row["costing_rate"], row["costing_amount"]), (9, 83.33, 499.98)
		)
		self.assertEqual(ts["total_costing_amount"], 499.98)

	def test_overtime_rows_use_the_overtime_rate(self):
		ts = self._save(
			[
				{"project": self.project, "hours": 8},
				{"project": self.project, "hours": 2, "is_overtime": 1},
			]
		)
		self.assertEqual([r["costing_rate"] for r in ts["rows"]], [83.33, 50])
		self.assertEqual(ts["rows"][1]["costing_amount"], 100)

	def test_recalculated_while_draft_and_frozen_on_submit(self):
		ts = self._save([{"project": self.project, "hours": 6}])
		frappe.db.set_value("Project", self.project, "full_day_hours", 10)
		ts = self._save([{"project": self.project, "hours": 6}], name=ts["name"])
		self.assertEqual((ts["rows"][0]["full_day_hours"], ts["rows"][0]["costing_rate"]), (10, 75))

		frappe.get_doc("Timesheet", ts["name"]).submit()
		frappe.db.set_value("Project", self.project, "full_day_hours", 12)
		frappe.db.set_value("Employee", self.worker, "custom_wage", 1200)
		after = api.get_timesheet(ts["name"])["rows"][0]
		self.assertEqual(
			(after["full_day_hours"], after["costing_rate"], after["costing_amount"]), (10, 75, 450)
		)

	def test_costing_info_for_the_form_text(self):
		info = api.costing_info(self.worker, self.project)
		self.assertEqual((info["daily_rate"], info["full_day_hours"], info["hourly_rate"]), (750, 9, 83.33))
		self.assertEqual(info["overtime_rate"], 50)

	def test_salaried_worker_is_still_costed_from_the_field_employee_wages(self):
		"""buildsuite_hr marks some workers "Salaried" and prices their attendance from a salary
		structure. A timesheet is costed from the Field Employee's Wage and Wage For Overtime only."""
		frappe.db.set_value("Employee", self.worker, "custom_labour_wage_type", "Salaried")
		with patch(
			"buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance.get_employee_rates",
			side_effect=AssertionError("a timesheet must not read a salary structure"),
		):
			ts = self._save(
				[
					{"project": self.project, "hours": 6},
					{"project": self.project, "hours": 2, "is_overtime": 1},
				]
			)
			info = api.costing_info(self.worker, self.project)
		# 750 a day / 9 h = 83.33; overtime is the worker's own hourly 50
		self.assertEqual([r["costing_rate"] for r in ts["rows"]], [83.33, 50])
		self.assertEqual(ts["total_costing_amount"], 599.98)
		self.assertEqual((info["daily_rate"], info["hourly_rate"], info["overtime_rate"]), (750, 83.33, 50))

	# --- cost code ---------------------------------------------------------
	def test_cost_code_is_kept_and_a_moved_row_loses_it(self):
		other = (
			frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"Other {self._n}",
					"custom_project_id": f"OTH-{self._n}",
					"project_status": "Ongoing",
					"company": self.company,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		with patch("buildsuite_core.api.subcontract.get_project_cost_codes", return_value=CODES):
			code = {"type": "item", "group_code": "B", "item_code": "B.04", "label": "B.04 · Wardrobes"}
			ts = self._save([{"project": self.project, "hours": 4, "cost_code": code}])
			self.assertEqual(ts["rows"][0]["cost_code"]["item_code"], "B.04")

			# the same row moved to another project is uncoded
			doc = frappe.get_doc("Timesheet", ts["name"])
			doc.time_logs[0].project = other
			doc.save()
			self.assertIsNone(api.get_timesheet(ts["name"])["rows"][0]["cost_code"])

	def test_a_code_not_on_the_estimate_is_refused(self):
		with patch("buildsuite_core.api.subcontract.get_project_cost_codes", return_value=CODES):
			bad = {"type": "item", "group_code": "Z", "item_code": "Z.99", "label": "Z.99 · Nope"}
			with self.assertRaisesRegex(frappe.ValidationError, "not on the estimate"):
				self._save([{"project": self.project, "hours": 4, "cost_code": bad}])

	# --- one worker, one day -----------------------------------------------
	def test_one_timesheet_per_worker_per_day_and_24_hours_a_day(self):
		self._save([{"project": self.project, "hours": 4}])
		with self.assertRaisesRegex(frappe.ValidationError, "already has a timesheet"):
			self._save([{"project": self.project, "hours": 2}])
		with self.assertRaisesRegex(frappe.ValidationError, "more than 24"):
			self._save(
				[{"project": self.project, "hours": 20}, {"project": self.project, "hours": 6}],
				date=frappe.utils.add_days(self.day, -3),
			)

	# --- the import plan ---------------------------------------------------
	def _plan(self, rows):
		header = [
			"Date",
			"Employee code",
			"Employee name",
			"Project code",
			"Cost code",
			"Hours",
			"Overtime (Y/N)",
			"Description",
		]
		with patch("buildsuite_core.api.timesheet._codes_for", return_value=CODES):
			return api.plan_import([header, *rows])

	def test_cost_code_forms_are_accepted_and_an_unknown_one_leaves_the_row_out(self):
		base = [self.day, self.worker, "", self.project]
		plan = self._plan(
			[
				[*base, "B", 2, "N", ""],
				[*base, "B.04", 2, "N", ""],
				[*base, "B.04 · Wardrobes", 2, "N", ""],
				[*base, "Z.99", 2, "N", ""],
			]
		)
		self.assertEqual(len(plan["groups"]), 1)
		self.assertEqual(
			[r["cost_code"]["item_code"] for r in plan["groups"][0]["rows"]], [None, "B.04", "B.04"]
		)
		self.assertEqual(len(plan["skipped"]), 1)
		self.assertEqual(
			plan["skipped"][0]["reason"],
			f'Cost code "Z.99" is not on the estimate of {frappe.db.get_value("Project", self.project, "project_name")}.',
		)

	def test_an_old_file_with_a_task_column_is_flagged_and_comes_in_uncoded(self):
		header = ["Date", "Employee code", "Project code", "Task", "Hours"]
		with patch("buildsuite_core.api.timesheet._codes_for", return_value=CODES):
			plan = api.plan_import([header, [self.day, self.worker, self.project, "Paint walls", 3]])
		self.assertTrue(plan["legacy_task"])
		self.assertIsNone(plan["groups"][0]["rows"][0]["cost_code"])
		self.assertEqual(plan["groups"][0]["rows"][0]["hours"], 3)

	def test_blank_hours_rows_are_ignored(self):
		plan = self._plan([[self.day, self.worker, "", self.project, "", "", "N", ""]])
		self.assertEqual((plan["groups"], plan["blank"]), ([], 1))

	# --- patch -------------------------------------------------------------
	def test_patch_sets_existing_rows_to_an_8_hour_day(self):
		from buildsuite_core.patches.set_timesheet_costing_defaults import execute

		ts = self._save([{"project": self.project, "hours": 5}])
		frappe.db.sql("UPDATE `tabTimesheet Detail` SET full_day_hours = 0 WHERE parent = %s", ts["name"])
		execute()
		self.assertEqual(api.get_timesheet(ts["name"])["rows"][0]["full_day_hours"], 8)
