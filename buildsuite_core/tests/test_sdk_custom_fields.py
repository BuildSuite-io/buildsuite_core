# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.tests import IntegrationTestCase

from buildsuite_core.sdk.custom_fields import apply_custom_fields, custom_field_values

DT = "Subcontractor Work Order"
FIELDS = ("sdk_t_region", "sdk_t_locked", "sdk_t_secret", "sdk_t_note")


class TestApplyCustomFields(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_fields(
			{
				DT: [
					{"fieldname": "sdk_t_region", "fieldtype": "Data", "label": "SDK T Region"},
					{
						"fieldname": "sdk_t_locked",
						"fieldtype": "Data",
						"label": "SDK T Locked",
						"read_only": 1,
					},
					{
						"fieldname": "sdk_t_secret",
						"fieldtype": "Data",
						"label": "SDK T Secret",
						"permlevel": 5,
					},
					{"fieldname": "sdk_t_note", "fieldtype": "Small Text", "label": "SDK T Note"},
				]
			}
		)

	@classmethod
	def tearDownClass(cls):
		for f in FIELDS:
			frappe.delete_doc("Custom Field", f"{DT}-{f}", force=True)
		frappe.db.commit()  # the fixtures' schema change must not leak
		frappe.clear_cache(doctype=DT)
		super().tearDownClass()

	def _doc(self):
		return frappe.new_doc(DT)

	def test_sets_declared_custom_fields_from_a_dict_or_json(self):
		doc = self._doc()
		self.assertEqual(apply_custom_fields(doc, {"sdk_t_region": "East"}), ["sdk_t_region"])
		self.assertEqual(doc.sdk_t_region, "East")
		apply_custom_fields(doc, frappe.as_json({"sdk_t_note": "hello"}))
		self.assertEqual(doc.sdk_t_note, "hello")

	def test_standard_fields_cannot_be_set_through_it(self):
		doc = self._doc()
		doc.owner = "Administrator"
		applied = apply_custom_fields(
			doc, {"owner": "attacker@example.com", "docstatus": 1, "total_value": 99}
		)
		self.assertEqual(applied, [])
		self.assertEqual(doc.owner, "Administrator")
		self.assertEqual(doc.docstatus, 0)
		self.assertFalse(doc.total_value)

	def test_read_only_and_higher_permlevel_custom_fields_are_skipped(self):
		doc = self._doc()
		applied = apply_custom_fields(doc, {"sdk_t_locked": "x", "sdk_t_secret": "y", "sdk_t_region": "ok"})
		self.assertEqual(applied, ["sdk_t_region"])

	def test_unknown_keys_and_bad_input_are_ignored(self):
		doc = self._doc()
		self.assertEqual(apply_custom_fields(doc, {"nope": 1}), [])
		self.assertEqual(apply_custom_fields(doc, None), [])
		self.assertEqual(apply_custom_fields(doc, "[1,2]"), [])

	def test_values_read_back_for_the_form(self):
		doc = self._doc()
		doc.sdk_t_region = "North"
		out = custom_field_values(doc)
		self.assertEqual(out["sdk_t_region"], "North")
		self.assertNotIn("owner", out)
		self.assertNotIn("total_value", out)
