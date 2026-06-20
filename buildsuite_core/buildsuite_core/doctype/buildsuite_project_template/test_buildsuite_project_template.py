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
