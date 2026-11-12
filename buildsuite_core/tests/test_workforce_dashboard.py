# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Workforce dashboard figures come from submitted attendance, not drafts."""

from unittest.mock import patch

import frappe

from buildsuite_core.api.field_attendance import save_field_attendance
from buildsuite_core.api.workforce import get_dashboard
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestWorkforceDashboard(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		trade = f"Trade {self._n}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": trade}).insert(ignore_permissions=True)
		self.project = self._make_project().name
		# Scope the dashboard to the company the test project landed in: with company awareness on, the
		# site's working company need not be the one a new project is created under.
		self.company = frappe.db.get_value("Project", self.project, "company")
		scope = patch("buildsuite_core.api.workforce.company_scope", return_value=self.company)
		scope.start()
		self.addCleanup(scope.stop)
		self.worker_a = self._worker(trade, 900)
		self.worker_b = self._worker(trade, 1100)
		self.today = frappe.utils.today()

	def _worker(self, trade, wage):
		return (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"naming_series": "HR-EMP-",
					"first_name": f"WF {frappe.generate_hash(length=4)}",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
					"status": "Active",
					"company": self.company,
					"is_labour": 1,
					"custom_trade": trade,
					"custom_wage": wage,
					"custom_wage_for_overtime": 50,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _sheet(self):
		return save_field_attendance(
			project=self.project,
			date=self.today,
			status="Present",
			employee_list=frappe.as_json(
				[
					{"employee": self.worker_a, "status": "Present", "overtime_hours": 2},
					{"employee": self.worker_b, "status": "Half Day", "overtime_hours": 0},
				]
			),
		)

	def test_dashboard_has_every_figure(self):
		d = get_dashboard()
		for key in ("active_workers", "active_crews", "man_days", "labour_cost"):
			self.assertIsInstance(d[key], int | float)
		self.assertIsInstance(d["recent_attendance"], list)
		self.assertIsInstance(d["recent_labour"], list)

	def test_dashboard_counts_submitted_attendance_only(self):
		before = get_dashboard()
		res = self._sheet()
		# A draft sheet is in neither register, so nothing moves — but it is "recent attendance".
		draft = get_dashboard()
		self.assertEqual(
			(draft["man_days"], draft["labour_cost"]), (before["man_days"], before["labour_cost"])
		)
		self.assertIn(res["name"], [a["name"] for a in draft["recent_attendance"]])

		frappe.get_doc("Field Attendance", res["name"]).submit()
		after = get_dashboard()
		# One full day + one half day = 1.5 man-days; cost = 900 + 2h OT @50 + 1100/2.
		self.assertAlmostEqual(after["man_days"] - before["man_days"], 1.5)
		self.assertAlmostEqual(after["labour_cost"] - before["labour_cost"], 900 + 2 * 50 + 1100 / 2)
		self.assertGreaterEqual(after["active_workers"], 2)  # the two workers made in setUp
