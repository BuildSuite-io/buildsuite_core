# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Labour Cost Summary: one reading of the registers, matching Site Attendance Summary for
attendance and the timesheets' own total for timesheets."""

from unittest.mock import patch

import frappe

from buildsuite_core.api import labour_cost_summary as api_summary
from buildsuite_core.tests import test_timesheet_registers as helpers


class TestLabourCostSummary(helpers.TestTimesheetRegisters):
	"""Reuses the registers test's builders; its own tests are removed below so they run once."""

	def setUp(self):
		super().setUp()
		scope = patch("buildsuite_core.api.labour_cost_summary.company_scope", return_value=self.company)
		scope.start()
		self.addCleanup(scope.stop)
		frappe.db.set_value("Project", self.project, "full_day_hours", 10)
		self._n = frappe.generate_hash(length=6)
		self.project2 = self._make_project().name
		frappe.db.set_value("Project", self.project2, "full_day_hours", 9)

	def _summary(self, **kw):
		return api_summary.get_summary(worker=self.worker, **kw)

	def _sas(self):
		"""What Site Attendance Summary adds up for this worker: attendance-sourced wages, overtime
		wages and man-days (full + half x 0.5)."""
		labour = frappe.get_all(
			"Labour Attendance Register",
			filters={"employee": self.worker, "docstatus": 1, "source": "Attendance"},
			fields=["status", "daily_wage_calculated"],
		)
		ot = frappe.get_all(
			"Overtime Attendance Register",
			filters={"employee": self.worker, "docstatus": 1, "source": "Attendance"},
			pluck="overtime_wage_calculated",
		)
		days = sum({"Full Day": 1, "Half Day": 0.5}.get(r.status, 0) for r in labour)
		return sum(r.daily_wage_calculated for r in labour) + sum(ot), days

	# --- the Done-when sums --------------------------------------------------
	def test_attendance_only_matches_site_attendance_summary(self):
		self._sheet([{"employee": self.worker, "status": "Present", "overtime_hours": 2}])
		cost, days = self._sas()
		t = self._summary()["totals"]
		self.assertAlmostEqual(t["total"], cost, places=2)
		self.assertAlmostEqual(t["man_days"], days, places=2)
		self.assertEqual(t["hours"], 10)  # a Present worker on a 10-hour project
		self.assertEqual(t["ot_hours"], 2)

	def test_timesheet_only_matches_the_timesheets_total(self):
		ts = self._timesheet(
			[
				{"project": self.project, "hours": 5},
				{"project": self.project2, "hours": 4.5},
				{"project": self.project, "hours": 2, "is_overtime": 1},
			]
		)
		res = self._summary(source="Timesheet")
		self.assertAlmostEqual(res["totals"]["total"], ts["total_costing_amount"], places=2)
		# Ganesh's split day: 5 h of a 10-hour day + 4.5 h of a 9-hour day = 1 man-day.
		self.assertAlmostEqual(res["totals"]["man_days"], 1.0, places=2)

	def test_mixed_period_is_attendance_plus_timesheets(self):
		self._sheet(
			[{"employee": self.worker, "status": "Half Day"}], date=frappe.utils.add_days(self.day, -1)
		)
		ts = self._timesheet([{"project": self.project, "hours": 4}])
		cost, _days = self._sas()
		t = self._summary()["totals"]
		self.assertAlmostEqual(t["total"], cost + ts["total_costing_amount"], places=2)

	# --- grouping ------------------------------------------------------------
	def test_by_project_by_worker_and_a_total_row_that_is_distinct(self):
		self._timesheet([{"project": self.project, "hours": 5}, {"project": self.project2, "hours": 4.5}])
		by_project = self._summary(group_by="project")
		self.assertEqual({r["key"] for r in by_project["rows"]}, {self.project, self.project2})
		self.assertEqual(by_project["totals"]["workers"], 1)  # one worker on two projects
		(row,) = self._summary(group_by="worker")["rows"]
		self.assertEqual((row["projects"], row["days_worked"], row["workers"]), (2, 1, 1))
		self.assertEqual(by_project["rows"], sorted(by_project["rows"], key=lambda r: -r["total"]))

	def test_by_cost_code_puts_rows_without_a_code_under_no_cost_code_per_project(self):
		self._timesheet(
			[
				{"project": self.project, "hours": 4, "cost_code": helpers.ITEM},
				{"project": self.project, "hours": 3},
			]
		)
		rows = {r["label"]: r for r in self._summary(group_by="code")["rows"]}
		self.assertEqual(rows["B.04"]["sub"], "Wardrobes")
		self.assertTrue(rows["No cost code"]["uncoded"])
		self.assertEqual(rows["No cost code"]["project"], self.project)

	def test_ot_share_is_ot_cost_over_total(self):
		self._timesheet(
			[
				{"project": self.project, "hours": 8},
				{"project": self.project, "hours": 4, "is_overtime": 1},
			]
		)
		(row,) = self._summary()["rows"]
		self.assertAlmostEqual(row["ot_share"], row["ot_cost"] / row["total"] * 100, places=4)

	def test_absent_rows_add_nothing_and_break_no_count(self):
		self._sheet([{"employee": self.worker, "status": "Absent"}])
		t = self._summary()["totals"]
		self.assertEqual((t["hours"], t["total"], t["days_worked"]), (0, 0, 0))

	# --- drafts and filters --------------------------------------------------
	def test_drafts_are_counted_but_not_costed(self):
		self._timesheet([{"project": self.project, "hours": 4}], submit=False)
		res = self._summary()
		self.assertEqual(res["drafts"], 1)
		self.assertEqual(res["totals"]["total"], 0)
		self.assertEqual(self._summary(source="Attendance")["drafts"], 0)

	def test_captured_as_period_and_project_filters(self):
		self._timesheet([{"project": self.project, "hours": 4}])
		self._sheet(
			[{"employee": self.worker, "status": "Present"}], date=frappe.utils.add_days(self.day, -3)
		)
		self.assertEqual(len(self._summary(source="Timesheet", group_by="project")["rows"]), 1)
		self.assertEqual(self._summary(from_date=self.day)["totals"]["hours"], 4)
		self.assertEqual(self._summary(project=self.project2)["rows"], [])


# The parent's tests belong to its own module; only this class's own tests run here.
for _name in [n for n in vars(helpers.TestTimesheetRegisters) if n.startswith("test_")]:
	if _name not in vars(TestLabourCostSummary):
		setattr(TestLabourCostSummary, _name, None)
