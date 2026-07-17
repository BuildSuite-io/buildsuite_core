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



class IntegrationTestEstimateTemplate(IntegrationTestCase):
	"""
	Integration tests for EstimateTemplate.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestEstimateTemplate(BuildSuiteTestCase):
	def _make_template(self, rows=None, project_category=None):
		return frappe.get_doc(
			{
				"doctype": "Estimate Template",
				"template_code": f"UAT-{frappe.generate_hash(length=6)}",
				"template_name": "UAT Template",
				"project_category": project_category,
				"rows": rows or [],
			}
		).insert(ignore_permissions=True)

	def test_estimate_template_creation(self):
		# EST-015 — a template can be created with a code, name and (optional)
		# project category, and is enabled by default.
		tpl = self._make_template()
		self.assertEqual(tpl.name, tpl.template_code)
		self.assertEqual(tpl.enabled, 1)

	def test_template_rows_amount_and_total(self):
		# EST-016 — a Resource row and an Assembly row each derive their
		# uom/rate/amount from the linked master, and the template rolls up
		# row_count + estimated_total across all rows.
		resource = self._make_rate_master(rate=200)
		asm = frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"UAT-ASM-{frappe.generate_hash(length=5)}",
				"assembly_name": "UAT Assembly",
				"uom": "Nos",
				"components": [{"resource": resource.name, "coefficient": 1}],
			}
		).insert(ignore_permissions=True)  # rate_per_unit = 200

		tpl = self._make_template(
			rows=[
				{"group_name": "G1", "line_type": "Resource", "resource": resource.name, "placeholder_qty": 3},
				{"group_name": "G1", "line_type": "Assembly", "assembly": asm.name, "placeholder_qty": 2},
			]
		)
		res_row, asm_row = tpl.rows[0], tpl.rows[1]
		self.assertEqual(res_row.uom, "Nos")
		self.assertEqual(res_row.rate, 200)
		self.assertEqual(res_row.amount, 600)  # 3 * 200

		self.assertEqual(asm_row.uom, "Nos")
		self.assertEqual(asm_row.rate, 200)  # assembly rate_per_unit
		self.assertEqual(asm_row.amount, 400)  # 2 * 200

		self.assertEqual(tpl.row_count, 2)
		self.assertEqual(tpl.estimated_total, 1000)

	def test_template_row_assembly_required_for_assembly_line_type(self):
		# _sync_row throws when line_type=Assembly but no assembly is linked
		# (found while exercising EST-016's row-sync logic).
		with self.assertRaises(frappe.ValidationError):
			self._make_template(rows=[{"group_name": "G1", "line_type": "Assembly"}])

	def test_multiple_templates_per_project_type_allowed(self):
		# EST-017 — two templates tagged to the same project category can both
		# exist; templates are not limited to one per category.
		category = frappe.db.get_value("Project Category", {}, "name")
		if not category:
			self.skipTest("No Project Category seeded on this site")
		t1 = self._make_template(project_category=category)
		t2 = self._make_template(project_category=category)
		tagged = frappe.get_all("Estimate Template", filters={"project_category": category}, pluck="name")
		self.assertIn(t1.name, tagged)
		self.assertIn(t2.name, tagged)

	def test_edit_template_row_recomputes_total(self):
		# _sync_row / estimated_total must also recompute on an UPDATE to an
		# existing template's row, not just at creation time.
		resource = self._make_rate_master(rate=200)
		tpl = self._make_template(
			rows=[{"group_name": "G1", "line_type": "Resource", "resource": resource.name, "placeholder_qty": 2}]
		)
		self.assertEqual(tpl.estimated_total, 400)  # 2 * 200

		tpl.rows[0].placeholder_qty = 5
		tpl.save(ignore_permissions=True)
		self.assertEqual(tpl.rows[0].amount, 1000)  # 5 * 200
		self.assertEqual(tpl.estimated_total, 1000)

	def test_delete_estimate_template(self):
		# An Estimate Template deletes cleanly — nothing else links to it (it's
		# only ever imported BY VALUE into a BOQ, never referenced by name).
		tpl = self._make_template()
		frappe.delete_doc("Estimate Template", tpl.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Estimate Template", tpl.name))
