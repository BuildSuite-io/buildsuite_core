# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The named save APIs (the bespoke forms that do not save through the generic resource write) carry an
extension's Custom Fields: Field Attendance, Field Employee, Material Consumption and Measurement Book.
The shared helper is unit tested in test_sdk_custom_fields; this is each save, end to end."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from buildsuite_core.api.field_attendance import save_field_attendance
from buildsuite_core.api.field_employee import ensure_labour_employment_type, save_field_employee
from buildsuite_core.api.material_consumption import save_material_consumption
from buildsuite_core.api.subcontract import save_measurement_book, save_work_order, submit_work_order
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.tests.test_field_employee import BASE as EMPLOYEE_BASE

FIELD = "sdk_t_named_region"
DOCTYPES = ("Employee", "Field Attendance", "Stock Entry", "Measurement Book")


class TestNamedSavesCarryCustomFields(BuildSuiteTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_fields(
			{dt: [{"fieldname": FIELD, "fieldtype": "Data", "label": "SDK T Region"}] for dt in DOCTYPES}
		)

	@classmethod
	def tearDownClass(cls):
		for dt in DOCTYPES:
			frappe.delete_doc("Custom Field", f"{dt}-{FIELD}", force=True)
			frappe.clear_cache(doctype=dt)
		frappe.db.commit()  # the fixtures' schema change must not leak
		super().tearDownClass()

	def _project(self):
		return self._make_project(company=self.company).name

	def _worker(self, trade):
		doc = frappe.get_doc(
			{
				**EMPLOYEE_BASE,
				"doctype": "Employee",
				"naming_series": "HR-EMP-",
				"first_name": f"UAT {frappe.generate_hash(length=4)}",
				"status": "Active",
				"company": self.company,
				"is_labour": 1,
				"employment_type": ensure_labour_employment_type(),
				"custom_trade": trade,
				"custom_wage": 900,
				"custom_wage_for_overtime": 50,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _trade(self):
		trade = f"Trade {frappe.generate_hash(length=4)}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": trade}).insert(ignore_permissions=True)
		return trade

	def test_field_employee(self):
		res = save_field_employee(
			**{
				**EMPLOYEE_BASE,
				"first_name": f"UAT {frappe.generate_hash(length=4)}",
				"company": self.company,
				"custom_trade": self._trade(),
				"custom_fields": frappe.as_json({FIELD: "Employee-East"}),
			}
		)
		self.assertEqual(frappe.db.get_value("Employee", res["name"], FIELD), "Employee-East")

	def test_field_attendance(self):
		res = save_field_attendance(
			project=self._project(),
			date=frappe.utils.today(),
			status="Present",
			employee_list=frappe.as_json([{"employee": self._worker(self._trade()), "status": "Present"}]),
			custom_fields=frappe.as_json({FIELD: "Sheet-North"}),
		)
		self.assertEqual(frappe.db.get_value("Field Attendance", res["name"], FIELD), "Sheet-North")
		self.assertEqual(res[FIELD], "Sheet-North")

	def test_material_consumption(self):
		project = self._project()
		from buildsuite_core.utils.stock_entry import get_warehouse_from_project

		if not get_warehouse_from_project(project):
			self.skipTest("the test project has no store")
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"UAT-CONS-{frappe.generate_hash(length=5)}",
				"item_name": "UAT consumable",
				"item_group": frappe.db.get_value("Item Group", {}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"valuation_rate": 10,  # a draft issue is valued at save
			}
		).insert(ignore_permissions=True)
		res = save_material_consumption(
			project=project,
			items=frappe.as_json([{"item_code": item.name, "qty": 1, "uom": "Nos"}]),
			custom_fields=frappe.as_json({FIELD: "Issue-West"}),
		)
		self.assertEqual(frappe.db.get_value("Stock Entry", res["name"], FIELD), "Issue-West")
		self.assertEqual(res[FIELD], "Issue-West")

	def test_measurement_book(self):
		project = self._project()
		sub = (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": f"Sub {self._n}",
					"supplier_type": "Subcontractor",
					"supplier_group": "Subcontractor",
					"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		wo = save_work_order(
			subcontractor=sub,
			project=project,
			date="2026-07-20",
			retention_percent=5,
			lines=frappe.as_json([{"scope": "Tiling", "uom": "Nos", "qty": 100, "rate": 85}]),
		)["name"]
		submit_work_order(wo)
		line = frappe.get_doc("Subcontractor Work Order", wo).lines[0].name
		res = save_measurement_book(
			work_order=wo,
			project=project,
			date="2026-07-21",
			entries=frappe.as_json([{"description": "Slab", "work_order_line": line, "quantity": 5}]),
			custom_fields=frappe.as_json({FIELD: "Book-South"}),
		)
		self.assertEqual(frappe.db.get_value("Measurement Book", res["name"], FIELD), "Book-South")
		self.assertEqual(res[FIELD], "Book-South")
