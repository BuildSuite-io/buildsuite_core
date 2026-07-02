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
	"""Seeding a project from its Project Category's ERPNext Project Template —
	work packages, stages and tasks, per the opt-in seed flags."""

	def _has_template(self):
		return frappe.db.exists("Project Template", {"project_category": "Commercial"})

	def _seeded_project(self, wps=False, stages=False, tasks=False):
		if not self._has_template():
			self.skipTest("No Commercial template seeded on this site")
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"SEED {self._n}",
				"custom_project_id": f"SEED-{self._n}",
				"company": self.company,
				"project_category": "Commercial",
				"custom_seed_default_work_packages": 1 if wps else 0,
				"custom_seed_default_stages": 1 if stages else 0,
				"custom_seed_default_tasks": 1 if tasks else 0,
			}
		).insert(ignore_permissions=True)

	def test_seed_stages_from_template(self):
		# Re-seed stages onto an EXISTING project from its category template.
		if not self._has_template():
			self.skipTest("No Commercial template seeded on this site")
		from buildsuite_core.utils.project import seed_stages_from_template

		p = self._make_project()
		frappe.db.set_value("Project", p.name, "project_category", "Commercial")
		res = seed_stages_from_template(p.name)
		self.assertGreater(res["seeded"], 0)
		self.assertTrue(frappe.get_all("Stage Planning", filters={"project": p.name}))

	# --- the seed-on-create modes ---------------------------------------
	def test_seed_mode_work_packages_and_tasks(self):
		# WPs + tasks on → tasks created and linked to the seeded work packages.
		p = self._seeded_project(wps=True, tasks=True)
		self.assertTrue(frappe.db.count("Work Package", {"project": p.name}))
		self.assertTrue(frappe.db.count("Task", {"project": p.name}))
		self.assertTrue(
			frappe.db.count("Task", {"project": p.name, "work_package": ("is", "set")})
		)

	def test_seed_mode_stages_only(self):
		# Stages on, tasks/WPs off → stages created; no tasks, no work packages.
		p = self._seeded_project(stages=True)
		self.assertTrue(frappe.db.count("Stage Planning", {"project": p.name}))
		self.assertEqual(frappe.db.count("Task", {"project": p.name}), 0)
		self.assertEqual(frappe.db.count("Work Package", {"project": p.name}), 0)

	def test_seed_mode_tasks_only(self):
		# Tasks on, stages/WPs off → tasks created; no stages.
		p = self._seeded_project(tasks=True)
		self.assertEqual(frappe.db.count("Stage Planning", {"project": p.name}), 0)
		self.assertTrue(frappe.db.count("Task", {"project": p.name}))
