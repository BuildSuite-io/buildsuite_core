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


class IntegrationTestConstructionRateMaster(IntegrationTestCase):
	"""
	Integration tests for ConstructionRateMaster.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestConstructionRateMaster(BuildSuiteTestCase):
	def test_rate_master_missing_mandatory_rejected(self):
		# EST-027 — current_rate and uom are mandatory; save is blocked when
		# either is missing. (category is also reqd=1, but Frappe auto-fills an
		# unset Select field from its first option on insert, so omitting it
		# never actually raises — see test_rate_master_category_defaults_when_omitted.)
		base = {
			"doctype": "Construction Rate Master",
			"rate_name": "UAT Rate",
			"category": "Material",
			"uom": "Nos",
			"current_rate": 100,
		}
		for missing in ("current_rate", "uom"):
			fields = {k: v for k, v in base.items() if k != missing}
			fields["rate_code"] = f"UAT-{frappe.generate_hash(length=5)}"
			with self.assertRaises(frappe.MandatoryError):
				frappe.get_doc(fields).insert(ignore_permissions=True)

	def test_rate_master_category_defaults_when_omitted(self):
		# A Select field with reqd=1 but no explicit default is auto-filled from
		# its first option by Frappe's own _set_defaults() on insert, so an
		# omitted category silently becomes "Material" rather than blocking save.
		doc = frappe.get_doc(
			{
				"doctype": "Construction Rate Master",
				"rate_code": f"UAT-{frappe.generate_hash(length=5)}",
				"rate_name": "UAT Rate",
				"uom": "Nos",
				"current_rate": 100,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.category, "Material")

	def test_add_rate_creates_master_with_open_history(self):
		# EST-023 — creating a rate seeds rate_history with a single open
		# ("Initial") row dated today, carrying the starting rate.
		rm = self._make_rate_master(rate=750)
		self.assertEqual(len(rm.rate_history), 1)
		row = rm.rate_history[0]
		self.assertEqual(row.rate, 750)
		self.assertEqual(row.reason, "Initial")
		self.assertEqual(frappe.utils.getdate(row.effective_from), frappe.utils.getdate())
		self.assertIsNone(row.effective_to)

	def test_edit_rate_archives_previous_via_history(self):
		# EST-024 — editing current_rate stamps previous_rate, closes the prior
		# open history row (effective_to = today) and appends a new open row
		# for the new rate.
		rm = self._make_rate_master(rate=750)
		rm.current_rate = 900
		rm.save(ignore_permissions=True)
		rm.reload()

		self.assertEqual(rm.previous_rate, 750)
		self.assertEqual(len(rm.rate_history), 2)

		initial, revised = rm.rate_history[0], rm.rate_history[1]
		self.assertEqual(initial.rate, 750)
		self.assertEqual(frappe.utils.getdate(initial.effective_to), frappe.utils.getdate())

		self.assertEqual(revised.rate, 900)
		self.assertEqual(revised.reason, "Manual revision")
		self.assertIsNone(revised.effective_to)

	def test_rate_master_resource_type_required_valid(self):
		# EST-027 — the resource-type classification (category: Material / Labour /
		# Equipment) is present on the doctype and persists on a valid record.
		rm = self._make_rate_master(category="Labour")
		self.assertEqual(rm.category, "Labour")

	def test_delete_rate_master(self):
		# An unreferenced Construction Rate Master deletes cleanly.
		rm = self._make_rate_master()
		frappe.delete_doc("Construction Rate Master", rm.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Construction Rate Master", rm.name))

	def test_rate_master_referenced_by_assembly_component_is_link_protected(self):
		# A Rate Master linked from an Assembly's component can't be deleted
		# while that link exists (Frappe link integrity) — disable it instead.
		rm = self._make_rate_master()
		frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"UAT-ASM-{frappe.generate_hash(length=5)}",
				"assembly_name": "UAT Assembly",
				"uom": "Nos",
				"components": [{"resource": rm.name, "coefficient": 1}],
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Construction Rate Master", rm.name, ignore_permissions=True)
