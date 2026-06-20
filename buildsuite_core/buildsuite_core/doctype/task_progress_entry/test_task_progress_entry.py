# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.tests.base import BuildSuiteTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestTaskProgressEntry(IntegrationTestCase):
	pass


class TestTaskProgressEntry(BuildSuiteTestCase):
	"""Filing a TPE drives the parent Task's progress/status; entries are
	monotonic; blockers need a note; deleting reverts the task."""

	def test_tpe_updates_task_status_and_no_throw(self):
		# TPE-006: 40% -> In Progress (previously threw on project.status="Working").
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)
		t.reload()
		self.assertEqual(t.progress, 40)
		self.assertEqual(t.task_status, "In Progress")

	def test_tpe_100_completes_task(self):
		# TPE-007
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 100)
		t.reload()
		self.assertEqual(t.progress, 100)
		self.assertEqual(t.task_status, "Completed")

	def test_delete_latest_tpe_reverts_to_previous(self):
		# TPE-009
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)
		latest = self._file_tpe(t.name, 100)
		t.reload()
		self.assertEqual(t.progress, 100)

		frappe.delete_doc("Task Progress Entry", latest.name, ignore_permissions=True)
		t.reload()
		self.assertEqual(t.progress, 40)
		self.assertEqual(t.task_status, "In Progress")

	def test_delete_only_tpe_reverts_to_zero(self):
		# TPE-010
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		only = self._file_tpe(t.name, 60)
		frappe.delete_doc("Task Progress Entry", only.name, ignore_permissions=True)
		t.reload()
		self.assertEqual(t.progress, 0)
		self.assertEqual(t.task_status, "Yet To Start")

	def test_blocker_requires_note(self):
		# TPE-011
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 30, blocker=1, blocker_detail=None)

	def test_blocker_with_note_ok(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 30, blocker=1, blocker_detail="Rain stopped the pour")
		self.assertTrue(tpe.name)

	def test_tpe_rejects_below_current_progress(self):
		# Progress is cumulative + monotonic — a lower entry is rejected (not logged).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 50)
		before = frappe.db.count("Task Progress Entry", {"task": t.name})

		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 40)  # below current 50% → rejected

		self.assertEqual(frappe.db.count("Task Progress Entry", {"task": t.name}), before)
		t.reload()
		self.assertEqual(t.progress, 50)

	def test_tpe_equal_and_increase_allowed(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 50)
		self._file_tpe(t.name, 50)   # equal — allowed
		self._file_tpe(t.name, 70)   # increase — allowed
		t.reload()
		self.assertEqual(t.progress, 70)
