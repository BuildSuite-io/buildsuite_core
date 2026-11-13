# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Day type (Regular / Off Day) rides from a Field Attendance sheet onto its Labour Attendance
Register rows; register_total can follow the list's search box."""

import json

import frappe

from buildsuite_core.api.field_attendance import register_total
from buildsuite_core.tests import test_timesheet_registers as helpers


class TestRegisterDayType(helpers.TestTimesheetRegisters):
	"""Reuses the registers test's builders; its own tests are removed below so they run once."""

	def _register_rows(self, sheet):
		return frappe.get_all(
			"Labour Attendance Register",
			filters={"field_attendance": sheet, "docstatus": 1},
			fields=["day_type", "status"],
		)

	def test_a_regular_sheet_gives_regular_register_rows(self):
		sheet = self._sheet([{"employee": self.worker, "status": "Present"}])
		self.assertEqual([r.day_type for r in self._register_rows(sheet)], ["Regular"])

	def test_an_off_day_sheet_gives_off_day_register_rows(self):
		res = helpers.save_field_attendance(
			project=self.project,
			date=self.day,
			status="Present",
			employee_list=frappe.as_json([{"employee": self.worker, "status": "Present"}]),
		)
		frappe.db.set_value("Field Attendance", res["name"], "day_type", "Off Day")
		frappe.get_doc("Field Attendance", res["name"]).submit()
		self.assertEqual([r.day_type for r in self._register_rows(res["name"])], ["Off Day"])

	def test_a_timesheet_row_is_a_regular_day(self):
		ts = self._timesheet([{"project": self.project, "hours": 4}])
		rows = frappe.get_all(
			"Labour Attendance Register", filters={"timesheet": ts["name"]}, fields=["day_type"]
		)
		self.assertEqual([r.day_type for r in rows], ["Regular"])

	def test_register_total_follows_or_filters(self):
		self._sheet([{"employee": self.worker, "status": "Present"}])
		everything = register_total(
			"Labour Attendance Register",
			"daily_wage_calculated",
			json.dumps([["employee", "=", self.worker]]),
		)
		self.assertGreater(everything, 0)
		named = register_total(
			"Labour Attendance Register",
			"daily_wage_calculated",
			json.dumps([["employee", "=", self.worker]]),
			json.dumps([["employee_name", "like", "%Reg%"]]),
		)
		other = register_total(
			"Labour Attendance Register",
			"daily_wage_calculated",
			json.dumps([["employee", "=", self.worker]]),
			json.dumps([["employee_name", "like", "%no-such-worker%"]]),
		)
		self.assertEqual(named, everything)
		self.assertEqual(other, 0)


# The parent's tests belong to its own module; only this class's own tests run here.
for _name in [n for n in vars(helpers.TestTimesheetRegisters) if n.startswith("test_")]:
	if _name not in vars(TestRegisterDayType):
		setattr(TestRegisterDayType, _name, None)
