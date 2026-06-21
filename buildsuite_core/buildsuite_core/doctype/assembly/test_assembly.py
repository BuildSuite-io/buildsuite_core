# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase


class TestAssembly(UnitTestCase):
	def setUp(self):
		self.uom = frappe.db.get_value("UOM", {}, "name")

	def _make_rate(self, rate):
		doc = frappe.get_doc({
			"doctype": "Construction Rate Master",
			"rate_code": f"RM-{frappe.generate_hash(length=6)}",
			"rate_name": "Test resource",
			"category": "Material",
			"uom": self.uom,
			"current_rate": rate,
		})
		doc.insert(ignore_permissions=True)
		return doc.name

	def _make_assembly(self, components):
		doc = frappe.get_doc({
			"doctype": "Assembly",
			"assembly_code": f"ASM-{frappe.generate_hash(length=6)}",
			"assembly_name": "Test assembly",
			"uom": self.uom,
			"components": components,
		})
		doc.insert(ignore_permissions=True)
		return doc

	def test_rate_rollup(self):
		resource = self._make_rate(1800)
		asm = self._make_assembly([
			{"resource": resource, "coefficient": 2},
			{"resource": resource, "coefficient": 1},
		])
		self.assertEqual(asm.components[0].amount, 3600)
		self.assertEqual(asm.components[1].amount, 1800)
		self.assertEqual(asm.rate_per_unit, 5400)
		self.assertEqual(asm.component_count, 2)

	def test_empty_assembly(self):
		asm = self._make_assembly([])
		self.assertEqual(asm.rate_per_unit, 0)
		self.assertEqual(asm.component_count, 0)
