# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for Stage Planning server-maintained aggregates — task_count,
mean_progress and completed_task_count (the "done / total" chip in the list).
completed_task_count must be a real count of member tasks at 100%, not the old
mean-progress estimate that rounded to 0 for stages under ~50% done."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestStagePlanningAggregates(BuildSuiteTestCase):
	def _make_stage(self, project, tasks):
		return frappe.get_doc(
			{
				"doctype": "Stage Planning",
				"project": project,
				"stage_name": f"Stage {self._n}",
				"stage_planning_tasks": [{"task": t} for t in tasks],
			}
		).insert(ignore_permissions=True)

	def _complete(self, task):
		task.task_status = "Completed"
		task.save(ignore_permissions=True)

	def test_completed_task_count_counts_completed_only(self):
		p = self._make_project(company=self.company)
		t1 = self._make_task(p.name, task_status="Completed")
		t2 = self._make_task(p.name, task_status="Yet To Start")
		t3 = self._make_task(p.name, task_status="In Progress")
		stage = self._make_stage(p.name, [t1.name, t2.name, t3.name])

		# One of three tasks is completed at insert time.
		self.assertEqual(stage.task_count, 3)
		self.assertEqual(stage.completed_task_count, 1)

	def test_completed_task_count_updates_when_member_task_completes(self):
		p = self._make_project(company=self.company)
		t1 = self._make_task(p.name, task_status="Yet To Start")
		t2 = self._make_task(p.name, task_status="Yet To Start")
		stage = self._make_stage(p.name, [t1.name, t2.name])
		self.assertEqual(stage.completed_task_count, 0)

		# Completing a member task recomputes the stage aggregate via the Task hook.
		self._complete(t1)
		self.assertEqual(
			frappe.db.get_value("Stage Planning", stage.name, "completed_task_count"), 1
		)

		self._complete(t2)
		self.assertEqual(
			frappe.db.get_value("Stage Planning", stage.name, "completed_task_count"), 2
		)

	def test_empty_stage_has_zero_completed(self):
		p = self._make_project(company=self.company)
		stage = self._make_stage(p.name, [])
		self.assertEqual(stage.task_count, 0)
		self.assertEqual(stage.completed_task_count, 0)
