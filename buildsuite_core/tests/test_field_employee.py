# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Field Employee save API over ERPNext Employee."""

import frappe

from buildsuite_core.api.field_employee import save_field_employee
from buildsuite_core.tests.base import BuildSuiteTestCase

BASE = {
	"gender": "Male",
	"date_of_birth": "1990-01-01",
	"date_of_joining": "2020-01-01",
	"custom_wage": 850,
}


class TestFieldEmployee(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.trade = f"Trade {frappe.generate_hash(length=4)}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": self.trade}).insert(ignore_permissions=True)

	def _save(self, **kwargs):
		payload = {
			**BASE,
			"first_name": f"UAT {frappe.generate_hash(length=4)}",
			"company": self.company,
			"custom_trade": self.trade,
		}
		payload.update(kwargs)
		return save_field_employee(**payload)

	def _project(self):
		n = frappe.generate_hash(length=6)
		doc = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {n}",
				"custom_project_id": f"UAT-{n}",
				"project_status": "Ongoing",
				"company": self.company,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_create_forces_is_labour(self):
		res = self._save()
		self.assertEqual(frappe.db.get_value("Employee", res["name"], "is_labour"), 1)

	def test_refuses_to_convert_a_non_field_employee(self):
		office = frappe.get_doc(
			{"doctype": "Employee", "naming_series": "HR-EMP-", "first_name": "Office", **BASE}
			| {"status": "Active", "company": self.company}
		)
		office.insert(ignore_permissions=True)
		with self.assertRaisesRegex(frappe.ValidationError, "not a field employee"):
			self._save(name=office.name, first_name="Hijacked")
		office.reload()
		self.assertEqual(office.is_labour, 0)
		self.assertNotEqual(office.first_name, "Hijacked")

	def test_partial_update_keeps_wage_and_status(self):
		# flt(None) is 0.0 and an omitted status used to default to Active, so a
		# partial update zeroed the wage and revived a departed worker.
		res = self._save(custom_wage_for_overtime=75, status="Inactive")
		self._save(name=res["name"], first_name="Renamed", custom_wage=None, status=None)
		kept = frappe.db.get_value(
			"Employee",
			res["name"],
			["custom_wage_for_overtime", "custom_wage", "status"],
			as_dict=True,
		)
		self.assertEqual(kept.custom_wage_for_overtime, 75)
		self.assertEqual(kept.custom_wage, 850)
		self.assertEqual(kept.status, "Inactive")

	def test_contractor_can_be_cleared(self):
		# Blank means "engaged directly", and the clear button posts null.
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"UAT Sub {frappe.generate_hash(length=4)}",
				"supplier_type": "Subcontractor",
			}
		).insert(ignore_permissions=True)

		res = self._save(custom_contractor=supplier.name)
		self.assertEqual(frappe.db.get_value("Employee", res["name"], "custom_contractor"), supplier.name)

		self._save(name=res["name"], custom_contractor=None)
		self.assertFalse(frappe.db.get_value("Employee", res["name"], "custom_contractor"))

	def test_allocations_are_saved_deduped_and_replaced(self):
		p1, p2 = self._project().name, self._project().name
		res = self._save(
			allocated_projects=frappe.as_json(
				[{"project": p1}, {"project": p1}, {"project": ""}, {"project": p2}]
			)
		)
		doc = frappe.get_doc("Employee", res["name"])
		self.assertEqual([r.project for r in doc.custom_project_assigned], [p1, p2])

		self._save(name=res["name"], allocated_projects=frappe.as_json([{"project": p2}]))
		doc.reload()
		self.assertEqual([r.project for r in doc.custom_project_assigned], [p2])

	def test_project_name_fetches_onto_the_row(self):
		project = self._project()
		res = self._save(allocated_projects=frappe.as_json([{"project": project.name}]))
		row = frappe.get_doc("Employee", res["name"]).custom_project_assigned[0]
		self.assertEqual(row.project_name, project.project_name)

	def test_blank_first_name_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "required"):
			self._save(first_name="  ")

	def test_unknown_name_does_not_create_a_duplicate(self):
		with self.assertRaisesRegex(frappe.ValidationError, "no longer exists"):
			self._save(name="HR-EMP-DOES-NOT-EXIST")

	def test_object_payload_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "list of rows"):
			self._save(allocated_projects=frappe.as_json({"project": "X"}))

	def test_company_falls_back_to_the_default(self):
		from buildsuite_core.utils.project import default_company

		res = self._save(company=None)
		self.assertEqual(frappe.db.get_value("Employee", res["name"], "company"), default_company())
