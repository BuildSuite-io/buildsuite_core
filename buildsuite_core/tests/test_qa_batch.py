# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Regression tests for the QA batch: project auto-Ongoing on task activity, and
Work Package code auto-generation."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestProjectAutoOngoing(BuildSuiteTestCase):
	def _status(self, project):
		return frappe.db.get_value("Project", project, "project_status")

	def test_new_project_flips_to_ongoing_on_progress_entry(self):
		p = self._make_project(status="New", company=self.company)
		t = self._make_task(p.name)
		# A brand-new task (Yet To Start, 0%) is not yet "work started".
		self.assertEqual(self._status(p.name), "New")
		# Filing a progress entry advances the task → project auto-advances to Ongoing.
		self._file_tpe(t.name, 30)
		self.assertEqual(self._status(p.name), "Ongoing")

	def test_new_project_flips_to_ongoing_on_task_status_change(self):
		p = self._make_project(status="New", company=self.company)
		t = self._make_task(p.name)
		t.task_status = "In Progress"
		t.save(ignore_permissions=True)
		self.assertEqual(self._status(p.name), "Ongoing")

	def test_completed_status_not_downgraded_by_task_activity(self):
		p = self._make_project(status="Completed", company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)
		self.assertEqual(self._status(p.name), "Completed")  # never auto-downgrades


class TestWorkPackageAutoCode(BuildSuiteTestCase):
	def _wp(self, project, name, code=None):
		doc = {"doctype": "Work Package", "project": project, "work_package_name": name}
		if code is not None:
			doc["code"] = code
		return frappe.get_doc(doc).insert(ignore_permissions=True)

	def test_blank_code_is_auto_generated_sequentially(self):
		p = self._make_project(company=self.company)
		a = self._wp(p.name, "Foundation")
		b = self._wp(p.name, "Structure")
		self.assertEqual(a.code, "WP-01")
		self.assertEqual(b.code, "WP-02")

	def test_explicit_code_is_preserved(self):
		p = self._make_project(company=self.company)
		wp = self._wp(p.name, "MEP", code="WP-MEP")
		self.assertEqual(wp.code, "WP-MEP")
