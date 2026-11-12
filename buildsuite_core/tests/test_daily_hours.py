# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""One worker, one day: regular time is at most one full day, all hours at most 24."""

import frappe

from buildsuite_core.api import timesheet as api
from buildsuite_core.tests import test_timesheet_registers as helpers


class TestDailyHours(helpers.TestTimesheetRegisters):
	"""Reuses the registers test's builders; its own tests are removed below so they run once."""

	def setUp(self):
		super().setUp()
		frappe.db.set_value("Project", self.project, "full_day_hours", 8)
		self._n = frappe.generate_hash(length=6)
		self.project2 = self._make_project().name
		frappe.db.set_value("Project", self.project2, "full_day_hours", 9)

	def _hours(self, hours, overtime=0, project=None, **kw):
		return self._timesheet(
			[{"project": project or self.project, "hours": hours, "is_overtime": overtime}], **kw
		)

	def _present(self, status="Present", **extra):
		return self._sheet([{"employee": self.worker, "status": status, **extra}])

	# --- a timesheet on its own ---------------------------------------------
	def test_regular_hours_over_a_full_day_are_refused(self):
		with self.assertRaisesRegex(
			frappe.ValidationError,
			r"12 regular hours is more than the 8-hour full day\. Enter the 4 hours beyond it as overtime",
		):
			self._hours(12, submit=False)

	def test_eight_regular_plus_four_overtime_is_accepted(self):
		self._timesheet(
			[
				{"project": self.project, "hours": 8},
				{"project": self.project, "hours": 4, "is_overtime": 1},
			]
		)

	def test_hours_are_counted_against_each_projects_own_full_day(self):
		frappe.db.set_value("Project", self.project, "full_day_hours", 10)
		ok = [{"project": self.project, "hours": 5}, {"project": self.project2, "hours": 4.5}]
		self._timesheet(ok, submit=False)  # 0.5 + 0.5 = 1.0 man-day
		bad = [{"project": self.project, "hours": 6}, {"project": self.project2, "hours": 4.5}]
		with self.assertRaisesRegex(frappe.ValidationError, "regular hours is more than"):
			self._timesheet(bad, submit=False, date=frappe.utils.add_days(self.day, 1))

	# --- timesheet after attendance -----------------------------------------
	def test_regular_timesheet_after_present_is_refused_but_overtime_is_accepted(self):
		self._present()
		with self.assertRaisesRegex(
			frappe.ValidationError, r"already has 8 regular hours that day on attendance, so no more regular"
		):
			self._hours(2, submit=False)
		self._hours(2, overtime=1)

	def test_half_day_leaves_room_for_half_a_day_of_timesheet(self):
		self._present("Half Day")
		with self.assertRaisesRegex(
			frappe.ValidationError, r"at most 4 regular hours fit here \(the full day is 8 hours\)"
		):
			self._hours(5, submit=False)
		self._hours(4)

	def test_a_timesheet_is_not_counted_against_itself(self):
		ts = self._hours(8, submit=False)
		doc = frappe.get_doc("Timesheet", ts["name"])
		doc.save()
		doc.submit()

	# --- attendance after a timesheet ---------------------------------------
	def test_present_after_a_timesheet_is_refused_but_half_day_is_accepted(self):
		self._hours(4)
		with self.assertRaisesRegex(
			frappe.ValidationError,
			r"4 regular hours on a timesheet that day and 8 here come to more than one full day \(8 hours\)",
		):
			self._present()
		self._present("Half Day")

	# --- the 24-hour ceiling -------------------------------------------------
	def test_attendance_plus_timesheet_overtime_cannot_pass_24_hours(self):
		self._present(overtime_hours=8)  # 8 regular + 8 overtime = 16
		with self.assertRaisesRegex(
			frappe.ValidationError,
			r"9 hours here and 16 already on attendance that day is more than 24 hours",
		):
			self._hours(9, overtime=1, submit=False)
		self._hours(8, overtime=1)

	# --- the upload preview --------------------------------------------------
	def test_the_upload_preview_marks_a_refused_day_as_a_problem(self):
		self._present()
		plan = api.plan_import(
			[
				["Employee Code", "Employee Name", "Date", "Project", "Cost Code", "Hours", "Overtime"],
				[self.worker, "", str(self.day), self.project, "", 3, ""],
			]
		)
		(group,) = plan["groups"]
		self.assertIn("no more regular hours fit", group["problem"])


# The parent's tests belong to its own module; only this class's own tests run here.
for _name in [n for n in vars(helpers.TestTimesheetRegisters) if n.startswith("test_")]:
	if _name not in vars(TestDailyHours):
		setattr(TestDailyHours, _name, None)
