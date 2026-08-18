# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for BuildSuite Task customisations: task_status <-> native status sync
(TSK-006/007) and single-assignee mapping onto Frappe-native _assign."""

import frappe
from frappe.utils import add_days, today

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestTask(BuildSuiteTestCase):
	def _make_wp(self, project, code_suffix=""):
		return frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": project,
				"work_package_name": f"WP {self._n}{code_suffix}",
				"code": f"WP-{self._n}{code_suffix}",
			}
		).insert(ignore_permissions=True)

	def test_task_status_syncs_to_native(self):
		# TSK-006 / TSK-007
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="Yet To Start")
		self.assertEqual(t.status, "Open")

		t.task_status = "In Progress"
		t.save(ignore_permissions=True)
		self.assertEqual(t.status, "Working")

	def test_task_status_defaults_to_yet_to_start(self):
		# TSK-006 — a new task with no explicit task_status defaults to
		# "Yet To Start" (the field's own default, not just a value we happen
		# to pass in every other test's helper call).
		p = self._make_project(company=self.company)
		t = frappe.get_doc({"doctype": "Task", "subject": f"UAT {self._n}", "project": p.name}).insert(
			ignore_permissions=True
		)
		self.assertEqual(t.task_status, "Yet To Start")

	def test_task_status_enum_complete(self):
		# TSK-007 — every allowed task_status value is accepted; an unknown
		# one is rejected outright.
		p = self._make_project(company=self.company)
		for status in ("Yet To Start", "In Progress", "In Delay", "Completed", "Blocked"):
			t = self._make_task(p.name, task_status=status)
			self.assertEqual(t.task_status, status)
		with self.assertRaises(frappe.ValidationError):
			self._make_task(p.name, task_status="Not A Real Status")

	def test_edit_to_belated_due_date_flags_in_delay(self):
		# Saving a not-done task with an end date already in the past marks it In Delay
		# on edit (parity with the create path and the nightly sweep), not only after the
		# next cron run.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="In Progress")
		t.exp_end_date = add_days(today(), -3)
		t.save(ignore_permissions=True)
		self.assertEqual(t.task_status, "In Delay")
		self.assertEqual(t.status, "Overdue")

	def test_edit_passed_start_unstarted_flags_in_delay(self):
		# A passed start date on unstarted work is late too; a manual In Progress is respected.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="Yet To Start")
		t.exp_start_date = add_days(today(), -2)
		t.save(ignore_permissions=True)
		self.assertEqual(t.task_status, "In Delay")

	def test_moving_due_date_forward_clears_in_delay(self):
		# The reverse transition: pushing the end date back to the future on an In Delay
		# task returns it to In Progress.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="In Progress")
		t.exp_end_date = add_days(today(), -3)
		t.save(ignore_permissions=True)
		self.assertEqual(t.task_status, "In Delay")
		t.exp_end_date = add_days(today(), 5)
		t.save(ignore_permissions=True)
		self.assertEqual(t.task_status, "In Progress")

	def test_completed_late_task_not_flagged_in_delay(self):
		# A 100%-complete task whose end date has passed settles to Completed, never In Delay.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="In Progress")
		t.exp_end_date = add_days(today(), -3)
		t.progress = 100
		t.task_status = "Completed"
		t.save(ignore_permissions=True)
		self.assertEqual(t.task_status, "Completed")
		self.assertEqual(t.status, "Completed")

	def test_blocked_task_not_auto_flagged_in_delay(self):
		# Blocked is an explicit manual state; a passed end date must not flip it to In Delay.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="Blocked")
		t.exp_end_date = add_days(today(), -3)
		t.save(ignore_permissions=True)
		self.assertEqual(t.task_status, "Blocked")

	def test_task_directly_under_project(self):
		# TSK-002: a task can be created with no work package.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self.assertFalse(t.work_package)

	# TSK-003 (task requires project) is enforced in the UI, not server-side
	# (ERPNext Task.project is optional) — covered by the Cypress suite.

	def test_task_type_defaults_to_activity(self):
		# TSK-004 — scheduling type lives on the native `type` Link (-> Task Type).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self.assertEqual(t.type, "Activity")

	def test_task_reassign_work_package(self):
		# TSK-010
		p = self._make_project(company=self.company)
		wp_a = self._make_wp(p.name, "A")
		wp_b = self._make_wp(p.name, "B")
		t = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"UAT {self._n}",
				"project": p.name,
				"work_package": wp_a.name,
			}
		).insert(ignore_permissions=True)
		t.work_package = wp_b.name
		t.save(ignore_permissions=True)
		t.reload()
		self.assertEqual(t.work_package, wp_b.name)

	def test_delete_task_cascades_tpes(self):
		# TSK-013: deleting a task removes its progress entries.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 30)
		frappe.delete_doc("Task", t.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Task", t.name))
		self.assertFalse(frappe.db.exists("Task Progress Entry", tpe.name))

	def test_delete_task_cascades_attachments(self):
		# TSK-013 — deleting a task also removes File attachments made against it
		# (cascade_delete_task doesn't stop at Task Progress Entries).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "note.txt",
				"attached_to_doctype": "Task",
				"attached_to_name": t.name,
				"content": "hello",
			}
		).insert(ignore_permissions=True)
		frappe.delete_doc("Task", t.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Task", t.name))
		self.assertFalse(frappe.db.exists("File", f.name))

	def test_task_company_derived_from_project(self):
		# TSK-011 — Task.company fetches from its project's company (a plain
		# fetch_from, not custom BuildSuite code, but worth locking in).
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self.assertEqual(t.company, self.company)

	def test_owner_stamped_on_create(self):
		# TSK-012: the creating user is recorded as the task owner.
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self.assertEqual(t.owner, frappe.session.user)

	def test_task_assignee_is_single_via_assign(self):
		"""Assignee maps to Frappe-native _assign with single-assignee semantics:
		reassigning drops the previous user; clearing empties it."""
		from buildsuite_core.api.task_assignment import get_task_assignee, set_task_assignee

		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		users = frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			pluck="name",
			limit=2,
		)
		if len(users) < 2:
			self.skipTest("needs at least two enabled System Users")
		u1, u2 = users[0], users[1]

		set_task_assignee(t.name, u1)
		self.assertEqual(get_task_assignee(t.name), u1)

		# Reassigning leaves exactly one open assignment, pointing at the new user.
		set_task_assignee(t.name, u2)
		self.assertEqual(get_task_assignee(t.name), u2)
		open_todos = frappe.get_all(
			"ToDo",
			filters={"reference_type": "Task", "reference_name": t.name, "status": ("!=", "Cancelled")},
			pluck="allocated_to",
		)
		self.assertEqual(open_todos, [u2])

		set_task_assignee(t.name, None)
		self.assertIsNone(get_task_assignee(t.name))
