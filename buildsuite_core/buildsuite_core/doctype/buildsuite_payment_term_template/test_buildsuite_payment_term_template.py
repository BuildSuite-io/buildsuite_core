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


class IntegrationTestBuildSuitePaymentTermTemplate(IntegrationTestCase):
	"""
	Integration tests for BuildSuitePaymentTermTemplate.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestBuildSuitePaymentTermTemplate(BuildSuiteTestCase):
	def _make_template(self, milestones):
		return frappe.get_doc(
			{
				"doctype": "BuildSuite Payment Term Template",
				"payment_term_name": f"UAT Terms {self._n}",
				"milestones": milestones,
			}
		).insert(ignore_permissions=True)

	def test_count_and_total_on_save(self):
		# Milestones adding up to 100% save, named after the template name,
		# enabled by default, with the count and total rolled up.
		tpl = self._make_template(
			[
				{"payable": "On signing", "percentage": 10},
				{"payable": "Stage completes", "stage": "Foundation", "percentage": 60},
				{"payable": "On a date", "days_after_project_start": 30, "percentage": 30},
			]
		)
		self.assertEqual(tpl.name, tpl.payment_term_name)
		self.assertEqual(tpl.enabled, 1)
		self.assertEqual(tpl.milestones_count, 3)
		self.assertEqual(tpl.total_percentage, 100)

	def test_total_must_be_100(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_template([{"payable": "On signing", "percentage": 90}])

	def test_no_milestones_is_allowed(self):
		tpl = self._make_template([])
		self.assertEqual(tpl.milestones_count, 0)
		self.assertEqual(tpl.total_percentage, 0)

	def test_unused_timing_is_cleared(self):
		# A row keeps only the timing its Payable uses.
		tpl = self._make_template(
			[
				{"payable": "On signing", "stage": "Foundation", "percentage": 50},
				{
					"payable": "Stage completes",
					"stage": "Roof",
					"days_after_project_start": 30,
					"percentage": 50,
				},
			]
		)
		signing, stage = tpl.milestones
		self.assertIsNone(signing.stage)
		self.assertIsNone(signing.days_after_project_start)
		self.assertEqual(stage.stage, "Roof")
		self.assertIsNone(stage.days_after_project_start)
