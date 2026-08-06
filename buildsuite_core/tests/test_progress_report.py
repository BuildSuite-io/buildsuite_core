# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Progress Report (S167) — the windowed aggregate."""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api import progress_report as pr
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestProgressReport(BuildSuiteTestCase):
	def test_report_shape_and_window(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="In Progress")
		self._file_tpe(t.name, 60)

		rep = pr.get_progress_report(p.name, period="weekly")
		# 7-day window ending today.
		self.assertEqual(rep["window"]["end"], nowdate())
		self.assertEqual(rep["window"]["start"], add_days(nowdate(), -6))
		# Structure the Vue renderer depends on.
		for key in (
			"project",
			"task_stats",
			"kpis",
			"task_activity",
			"stages",
			"materials",
			"look_ahead_tasks",
		):
			self.assertIn(key, rep)
		self.assertEqual(rep["project"]["id"], p.name)
		self.assertEqual(rep["task_stats"]["total"], 1)
		# The progress entry filed today falls in the window → 1 entry, task touched.
		self.assertEqual(rep["kpis"]["entries"], 1)
		self.assertIn(t.name, [r["id"] for r in rep["task_activity"]])
		# Enriched payload the client report renders.
		self.assertEqual(rep["audience"], "client")
		for key in ("programme", "variations", "photos", "company"):
			self.assertIn(key, rep)
		for key in ("actual", "expected", "slip_days", "variance", "days_left"):
			self.assertIn(key, rep["programme"])

	def test_invalid_period_and_audience_default(self):
		p = self._make_project(company=self.company)
		rep = pr.get_progress_report(p.name, period="fortnightly", audience="press")
		self.assertEqual(rep["period"], "weekly")
		self.assertEqual(rep["audience"], "client")

	def test_missing_project_throws(self):
		self.assertRaises(frappe.ValidationError, pr.get_progress_report, project="NOPE-DOES-NOT-EXIST")
