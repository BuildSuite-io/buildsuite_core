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


class IntegrationTestBuildSuiteProjectTemplate(IntegrationTestCase):
	pass


class TestBuildSuiteProjectTemplate(BuildSuiteTestCase):
	"""PTT-005 — seeding stages onto an existing project from its Project Type
	template, with template tasks at 100% planned qty."""

	def test_seed_stages_from_template(self):
		if not frappe.db.exists("BuildSuite Project Template", {"project_type": "Commercial"}):
			self.skipTest("No Commercial template seeded on this site")
		from buildsuite_core.utils.project import seed_stages_from_template

		p = self._make_project()
		frappe.db.set_value("Project", p.name, "project_type", "Commercial")
		res = seed_stages_from_template(p.name)
		self.assertGreater(res["seeded"], 0)

		stages = frappe.get_all("Stage Planning", filters={"project": p.name}, pluck="name")
		self.assertTrue(stages)
		for s in stages:
			for r in frappe.get_doc("Stage Planning", s).stage_planning_tasks:
				self.assertEqual(r.planned_qty, 100)

	# --- the three seed-on-create modes (PTT-001) --------------------------
	def _seeded_project(self, stages, tasks):
		"""Create a Commercial project with the given seed flags so the
		after_insert template hook fires. Skips when no template is seeded."""
		if not frappe.db.exists("BuildSuite Project Template", {"project_type": "Commercial"}):
			self.skipTest("No Commercial template seeded on this site")
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"SEED {self._n}",
				"custom_project_id": f"SEED-{self._n}",
				"company": self.company,
				"project_type": "Commercial",
				"custom_seed_default_stages": 1 if stages else 0,
				"custom_seed_default_tasks": 1 if tasks else 0,
			}
		).insert(ignore_permissions=True)

	def test_seed_mode_stages_and_tasks(self):
		# Both on → stages created WITH nested tasks, plus project-level tasks.
		p = self._seeded_project(stages=True, tasks=True)
		stages = frappe.get_all("Stage Planning", {"project": p.name}, pluck="name")
		self.assertTrue(stages)
		self.assertTrue(frappe.db.count("Task", {"project": p.name}))
		nested = any(frappe.get_doc("Stage Planning", s).stage_planning_tasks for s in stages)
		self.assertTrue(nested, "stages should carry nested tasks in this mode")

	def test_seed_mode_stages_only(self):
		# Stages on, tasks off → empty stages, NO tasks created.
		p = self._seeded_project(stages=True, tasks=False)
		stages = frappe.get_all("Stage Planning", {"project": p.name}, pluck="name")
		self.assertTrue(stages)
		self.assertEqual(frappe.db.count("Task", {"project": p.name}), 0)
		for s in stages:
			self.assertEqual(len(frappe.get_doc("Stage Planning", s).stage_planning_tasks), 0)

	def test_seed_mode_tasks_only(self):
		# Tasks on, stages off → no stages; every template task (project-level and
		# the ones nested in stage plans) lands as a plain project task.
		p = self._seeded_project(stages=False, tasks=True)
		self.assertEqual(frappe.db.count("Stage Planning", {"project": p.name}), 0)
		self.assertTrue(frappe.db.count("Task", {"project": p.name}))
