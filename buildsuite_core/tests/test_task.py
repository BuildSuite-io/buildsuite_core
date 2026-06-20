# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for BuildSuite Task customisations: task_status <-> native status sync
(TSK-006/007) and single-assignee mapping onto Frappe-native _assign."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestTask(BuildSuiteTestCase):
	def test_task_status_syncs_to_native(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="Yet To Start")
		self.assertEqual(t.status, "Open")

		t.task_status = "In Progress"
		t.save(ignore_permissions=True)
		self.assertEqual(t.status, "Working")

	def test_task_assignee_is_single_via_assign(self):
		"""Assignee maps to Frappe-native _assign with single-assignee semantics:
		reassigning drops the previous user; clearing empties it."""
		from buildsuite_core.api.task_assignment import set_task_assignee, get_task_assignee

		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		users = frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"},
			pluck="name", limit=2,
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
