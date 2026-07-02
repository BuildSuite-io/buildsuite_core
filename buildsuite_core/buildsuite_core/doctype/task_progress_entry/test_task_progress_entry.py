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

	def test_file_entry_links_to_task(self):
		# TPE-001
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 30)
		self.assertTrue(tpe.name)
		self.assertEqual(tpe.task, t.name)

	def test_progress_is_cumulative_not_delta(self):
		# TPE-002: task at 30, file 50 -> task is 50 (not 80).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 30)
		self._file_tpe(t.name, 50)
		t.reload()
		self.assertEqual(t.progress, 50)

	def test_latest_entry_is_source_of_truth(self):
		# TPE-008: the most recent entry drives the task, regardless of file order.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)
		self._file_tpe(t.name, 70)
		t.reload()
		self.assertEqual(t.progress, 70)

	def test_labour_and_weather_persist(self):
		# TPE-012
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = frappe.get_doc(
			{
				"doctype": "Task Progress Entry",
				"task": t.name,
				"entry_date": frappe.utils.today(),
				"cumulative_progress": 20,
				"skilled": 5,
				"unskilled": 8,
				"weather": "Rainy",
			}
		).insert(ignore_permissions=True)
		tpe.reload()
		self.assertEqual(tpe.skilled, 5)
		self.assertEqual(tpe.unskilled, 8)
		self.assertEqual(tpe.weather, "Rainy")

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

	def test_completed_task_rejects_new_entry(self):
		# A completed task takes no further progress entries — enforced in the
		# controller so it holds from the form, the TPE list, and the API alike.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 100)
		t.reload()
		self.assertEqual(t.task_status, "Completed")
		before = frappe.db.count("Task Progress Entry", {"task": t.name})
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 100)
		self.assertEqual(frappe.db.count("Task Progress Entry", {"task": t.name}), before)

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

	def test_tpe_equal_rejected_and_increase_allowed(self):
		# Strict-increase: re-filing the current value (a no-op duplicate) is rejected;
		# only a higher value is accepted and persisted.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 50)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 50)  # equal — rejected (no progress made)
		self._file_tpe(t.name, 70)  # increase — allowed
		t.reload()
		self.assertEqual(t.progress, 70)
		self.assertEqual(frappe.db.count("Task Progress Entry", {"task": t.name}), 2)

	def test_tpe_zero_rejected(self):
		# A progress entry of 0% records no progress and must never persist.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 0)
		self.assertEqual(frappe.db.count("Task Progress Entry", {"task": t.name}), 0)

	def test_tpe_noop_edit_rejected(self):
		# Opening an entry and saving with nothing changed is blocked (no duplicate).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 40)
		tpe.reload()
		with self.assertRaises(frappe.ValidationError):
			tpe.save(ignore_permissions=True)

	def test_progress_out_of_range_rejected(self):
		# TPE-003: a value above 100 or below 0 is rejected (never persisted).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 150)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, -10)
		self.assertEqual(frappe.db.count("Task Progress Entry", {"task": t.name}), 0)

	def test_tpe_rolls_up_through_wp_subproject_and_parent(self):
		# A single TPE drives the whole chain: task -> Work Package -> (sub)project
		# -> parent project. (Stage Planning shows the task's live status; there is
		# no separate stored stage progress — the stage sync only propagates dates.)
		parent = self._make_project(company=self.company)
		parent.is_group = 1
		parent.save(ignore_permissions=True)

		sub = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"ROLL sub {self._n}",
				"custom_project_id": f"ROLL-SUB-{self._n}",
				"parent_project": parent.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": sub.name,
				"work_package_name": f"ROLL WP {self._n}",
				"code": f"ROLL-WP-{self._n}",
				"status": "Planned",
			}
		).insert(ignore_permissions=True)

		t = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"ROLL task {self._n}",
				"project": sub.name,
				"work_package": wp.name,
				"task_status": "Yet To Start",
			}
		).insert(ignore_permissions=True)

		self._file_tpe(t.name, 100)

		t.reload()
		self.assertEqual(t.progress, 100)
		self.assertEqual(frappe.db.get_value("Work Package", wp.name, "progress"), 100)
		self.assertEqual(frappe.db.get_value("Work Package", wp.name, "status"), "Completed")
		self.assertEqual(frappe.db.get_value("Project", sub.name, "percent_complete"), 100)
		self.assertEqual(frappe.db.get_value("Project", parent.name, "percent_complete"), 100)
