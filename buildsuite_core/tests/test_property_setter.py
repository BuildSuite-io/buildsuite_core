# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Property setters are written only when they change (utils.property_setter) — migrate no longer
deletes and re-inserts every BuildSuite setter each run."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.property_setter import (
	CREATED,
	UNCHANGED,
	UPDATED,
	ensure_property_setter,
)

# A property nothing else sets, on a field every site has.
ARGS = {
	"doctype": "ToDo",
	"fieldname": "description",
	"property": "bold",
	"value": "1",
	"property_type": "Check",
}
FILTERS = {"doc_type": "ToDo", "field_name": "description", "property": "bold"}


class TestPropertySetter(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.delete("Property Setter", FILTERS)

	def _rows(self):
		return frappe.get_all("Property Setter", filters=FILTERS, fields=["name", "value"])

	def test_a_missing_setter_is_created(self):
		self.assertEqual(ensure_property_setter(ARGS), CREATED)
		self.assertEqual([r.value for r in self._rows()], ["1"])

	def test_the_same_value_again_leaves_the_row_alone(self):
		ensure_property_setter(ARGS)
		before = self._rows()
		deleted = frappe.db.count("Deleted Document", {"deleted_doctype": "Property Setter"})
		self.assertEqual(ensure_property_setter(ARGS), UNCHANGED)
		self.assertEqual(self._rows(), before)  # same row, same name
		self.assertEqual(frappe.db.count("Deleted Document", {"deleted_doctype": "Property Setter"}), deleted)

	def test_a_new_value_updates_the_row_in_place(self):
		ensure_property_setter(ARGS)
		[before] = self._rows()
		self.assertEqual(ensure_property_setter({**ARGS, "value": "0"}), UPDATED)
		[after] = self._rows()
		self.assertEqual(after.name, before.name)
		self.assertEqual(after.value, "0")

	def test_migrate_setters_are_unchanged_on_a_second_run(self):
		from buildsuite_core.custom_property_list.property_field import get_property_setters
		from buildsuite_core.install import make_property_setters

		make_property_setters()
		results = {ensure_property_setter(ps) for ps in get_property_setters()}
		self.assertEqual(results, {UNCHANGED})
