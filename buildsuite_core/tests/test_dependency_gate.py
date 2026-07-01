# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Finish-to-Start gate: a task can't start (move past Yet To Start / Blocked, or
log progress) while an FS predecessor isn't Completed. A negative lag is a lead, so
overlap is allowed and doesn't gate; SS/FF edges don't gate either."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestDependencyGate(BuildSuiteTestCase):
	def _link(self, successor, predecessor, dependency_type="FS", lag_days=0):
		successor.append(
			"depends_on",
			{"task": predecessor.name, "dependency_type": dependency_type, "lag_days": lag_days},
		)
		successor.save(ignore_permissions=True)
		return successor

	# --- gated -----------------------------------------------------------
	def test_fs_incomplete_blocks_status_change(self):
		p = self._make_project(company=self.company)
		a, b = self._make_task(p.name), self._make_task(p.name)
		self._link(b, a)  # B --FS--> A, A not Completed
		b.task_status = "In Progress"
		with self.assertRaises(frappe.ValidationError):
			b.save(ignore_permissions=True)

	def test_fs_incomplete_blocks_progress_entry(self):
		p = self._make_project(company=self.company)
		a, b = self._make_task(p.name), self._make_task(p.name)
		self._link(b, a)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(b.name, 30)
		self.assertEqual(frappe.db.count("Task Progress Entry", {"task": b.name}), 0)

	def test_blocked_status_is_allowed(self):
		# "Blocked" is permitted even with an open predecessor.
		p = self._make_project(company=self.company)
		a, b = self._make_task(p.name), self._make_task(p.name)
		self._link(b, a)
		b.task_status = "Blocked"
		b.save(ignore_permissions=True)  # no throw

	# --- ungated ---------------------------------------------------------
	def test_completed_predecessor_unblocks(self):
		p = self._make_project(company=self.company)
		a, b = self._make_task(p.name), self._make_task(p.name)
		self._link(b, a)
		self._file_tpe(a.name, 100)  # A -> Completed
		self._file_tpe(b.name, 30)  # now allowed
		self.assertEqual(frappe.db.get_value("Task", b.name, "task_status"), "In Progress")

	def test_negative_lag_is_a_lead_and_does_not_block(self):
		p = self._make_project(company=self.company)
		a, b = self._make_task(p.name), self._make_task(p.name)
		self._link(b, a, lag_days=-2)  # lead → overlap allowed
		self._file_tpe(b.name, 30)  # no throw

	def test_ss_dependency_does_not_block(self):
		p = self._make_project(company=self.company)
		a, b = self._make_task(p.name), self._make_task(p.name)
		self._link(b, a, dependency_type="SS")
		self._file_tpe(b.name, 30)  # no throw (only FS gates)
