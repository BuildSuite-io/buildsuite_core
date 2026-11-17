# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""A submitted timesheet writes the labour registers; labour_cost_rows is the one reader of them."""

from unittest.mock import patch

import frappe

from buildsuite_core.api import timesheet as api
from buildsuite_core.api.boq_actuals import _labour_entries
from buildsuite_core.api.field_attendance import save_field_attendance
from buildsuite_core.api.field_employee import ensure_labour_employment_type
from buildsuite_core.api.workforce import get_dashboard
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.labour_cost import cost_of, labour_cost_rows, totals

CODES = [
	{"type": "Group", "group_code": "B", "item_code": "", "label": "B · Joinery"},
	{"type": "Item", "group_code": "B", "item_code": "B.04", "label": "B.04 · Wardrobes"},
]
ITEM = {"type": "item", "group_code": "B", "item_code": "B.04", "label": "B.04 · Wardrobes"}


class TestTimesheetRegisters(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		trade = f"Trade {self._n}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": trade}).insert(ignore_permissions=True)
		self.project = self._make_project().name
		self.company = frappe.db.get_value("Project", self.project, "company")
		frappe.db.set_value("Project", self.project, "full_day_hours", 9)
		self.worker = self._worker(trade, 750, 50)
		self.day = frappe.utils.today()
		scope = patch("buildsuite_core.api.workforce.company_scope", return_value=self.company)
		scope.start()
		self.addCleanup(scope.stop)

	def _worker(self, trade, wage, ot):
		return (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"naming_series": "HR-EMP-",
					"first_name": f"Reg {frappe.generate_hash(length=4)}",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"company": self.company,
					"is_labour": 1,
					"employment_type": ensure_labour_employment_type(),
					"custom_trade": trade,
					"custom_wage": wage,
					"custom_wage_for_overtime": ot,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _timesheet(self, rows, submit=True, **kw):
		with patch("buildsuite_core.api.subcontract.get_project_cost_codes", return_value=CODES):
			return api.save_timesheet(
				employee=kw.pop("employee", self.worker),
				date=kw.pop("date", self.day),
				time_logs=frappe.as_json(rows),
				submit=1 if submit else 0,
			)

	def _sheet(self, rows, date=None):
		res = save_field_attendance(
			project=self.project, date=date or self.day, status="Present", employee_list=frappe.as_json(rows)
		)
		frappe.get_doc("Field Attendance", res["name"]).submit()
		return res["name"]

	def _rows(self, **f):
		return labour_cost_rows({"worker": self.worker, **f})

	# --- on_submit ----------------------------------------------------------
	def test_each_row_becomes_a_register_row(self):
		ts = self._timesheet(
			[
				{"project": self.project, "hours": 6, "cost_code": ITEM, "description": "Fit doors"},
				{"project": self.project, "hours": 2, "is_overtime": 1},
			]
		)
		labour = frappe.get_all(
			"Labour Attendance Register",
			filters={"timesheet": ts["name"], "docstatus": 1},
			fields=["*"],
		)
		self.assertEqual(len(labour), 1)
		row = labour[0]
		self.assertEqual(
			(row.status, row.source, row.regular_hours, row.full_day_hours), ("Hours", "Timesheet", 6, 9)
		)
		# priced at the timesheet row's rate: 750 / 9 = 83.33 an hour; wage_rate = rate x full day
		self.assertEqual((row.wage_rate, row.daily_wage_calculated), (749.97, 499.98))
		self.assertEqual(
			(row.cost_code_item, row.cost_code_label, row.comments), ("B.04", "B.04 · Wardrobes", "Fit doors")
		)
		self.assertEqual(row.timesheet_detail, ts["rows"][0]["name"])

		ot = frappe.get_all(
			"Overtime Attendance Register", filters={"timesheet": ts["name"], "docstatus": 1}, fields=["*"]
		)
		self.assertEqual(len(ot), 1)
		self.assertEqual(
			(ot[0].overtime_hours, ot[0].overtime_rate, ot[0].overtime_wage_calculated, ot[0].source),
			(2, 50, 100, "Timesheet"),
		)

	def test_register_rows_add_up_to_the_timesheet(self):
		ts = self._timesheet(
			[{"project": self.project, "hours": 6}, {"project": self.project, "hours": 2, "is_overtime": 1}]
		)
		rows = self._rows(source="Timesheet")
		t = totals(rows)
		self.assertEqual(round(t["cost"], 2), ts["total_costing_amount"])
		self.assertEqual(t["regular_hours"] + t["ot_hours"], ts["total_hours"])

	# --- the reader ---------------------------------------------------------
	def test_man_days_come_from_hours_and_each_row_counts_once(self):
		self._timesheet([{"project": self.project, "hours": 4.5}])  # half of a 9-hour day
		self._sheet(
			[{"employee": self.worker, "status": "Half Day"}], date=frappe.utils.add_days(self.day, -1)
		)
		rows = self._rows()
		self.assertEqual(len(rows), 2)
		self.assertEqual(sorted(round(r["man_days"], 2) for r in rows), [0.5, 0.5])
		self.assertEqual({r["source"] for r in rows}, {"Timesheet", "Attendance"})
		self.assertEqual(len(self._rows(source="Attendance")), 1)
		self.assertEqual(len(self._rows(source="Timesheet")), 1)

	def test_filters_project_worker_and_dates(self):
		self._timesheet([{"project": self.project, "hours": 4}])
		self.assertEqual(len(labour_cost_rows({"project": self.project, "worker": self.worker})), 1)
		self.assertEqual(labour_cost_rows({"project": self.project, "worker": "nobody"}), [])
		self.assertEqual(labour_cost_rows({"projects": []}), [])
		self.assertEqual(len(self._rows(**{"from": self.day, "to": self.day})), 1)
		self.assertEqual(self._rows(**{"from": frappe.utils.add_days(self.day, 1)}), [])

	def test_a_row_takes_its_sheets_cost_code_when_it_has_none(self):
		sheet = self._sheet([{"employee": self.worker, "status": "Present"}])
		frappe.db.set_value(
			"Field Attendance",
			sheet,
			{
				"cost_code_type": "Group",
				"cost_code_group": "B",
				"cost_code_item": "",
				"cost_code_label": "B · Joinery",
			},
		)
		row = self._rows()[0]
		self.assertEqual((row["cost_code"] or {}).get("group_code"), "B")

	def test_boq_actual_reads_both_sources_once_each(self):
		ts = self._timesheet([{"project": self.project, "hours": 6, "cost_code": ITEM}])
		sheet = self._sheet(
			[{"employee": self.worker, "status": "Present"}], date=frappe.utils.add_days(self.day, -1)
		)
		frappe.db.set_value(
			"Field Attendance",
			sheet,
			{
				"cost_code_type": "Group",
				"cost_code_group": "B",
				"cost_code_item": "",
				"cost_code_label": "B · Joinery",
			},
		)
		entries = _labour_entries(self.project)
		by_source = {e["source"]: e for e in entries}
		self.assertEqual(len(entries), 2)
		self.assertEqual(by_source["Timesheet"]["timesheet"], ts["name"])
		self.assertEqual(round(by_source["Timesheet"]["amount"], 2), 499.98)
		self.assertEqual(by_source["Attendance"]["field_attendance"], sheet)
		self.assertEqual(by_source["Attendance"]["unit"], "day")

	# --- cancel / delete ----------------------------------------------------
	def test_cancelling_a_timesheet_removes_its_rows_from_every_reading(self):
		ts = self._timesheet(
			[
				{"project": self.project, "hours": 6, "cost_code": ITEM},
				{"project": self.project, "hours": 1, "is_overtime": 1},
			]
		)
		self.assertTrue(self._rows(source="Timesheet"))
		self.assertTrue(_labour_entries(self.project))

		frappe.get_doc("Timesheet", ts["name"]).cancel()

		for dt in ("Labour Attendance Register", "Overtime Attendance Register"):
			self.assertFalse(frappe.db.exists(dt, {"timesheet": ts["name"], "docstatus": 1}))
		self.assertEqual(self._rows(source="Timesheet"), [])
		self.assertEqual(_labour_entries(self.project), [])

	def test_deleting_a_cancelled_timesheet_deletes_its_rows(self):
		ts = self._timesheet([{"project": self.project, "hours": 3}])
		doc = frappe.get_doc("Timesheet", ts["name"])
		doc.cancel()
		frappe.delete_doc("Timesheet", ts["name"], ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Labour Attendance Register", {"timesheet": ts["name"]}))

	# --- dashboards ---------------------------------------------------------
	def test_the_workforce_dashboard_counts_timesheets_too(self):
		before = get_dashboard()
		self._timesheet(
			[
				{"project": self.project, "hours": 9},
			]
		)
		after = get_dashboard()
		self.assertAlmostEqual(after["man_days"] - before["man_days"], 1.0, places=1)
		self.assertAlmostEqual(after["labour_cost"] - before["labour_cost"], 750.0, places=1)

	# --- a worker can't log more than 24 hours across both sources ---------
	def test_attendance_and_timesheet_together_cannot_pass_24_hours(self):
		self._sheet([{"employee": self.worker, "status": "Present", "overtime_hours": 10}])  # 9 + 10 = 19
		with self.assertRaisesRegex(frappe.ValidationError, "more than 24 hours"):
			self._timesheet([{"project": self.project, "hours": 6, "is_overtime": 1}])  # + 6 = 25
