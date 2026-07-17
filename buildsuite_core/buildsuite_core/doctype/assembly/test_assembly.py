# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestAssembly(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
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

	def test_component_links_rate_master_and_snapshots_rate(self):
		# EST-002 — a component's rate/uom are fetched from its linked resource,
		# and re-fetched (live, not frozen) on every subsequent assembly save.
		resource = self._make_rate(500)
		asm = self._make_assembly([{"resource": resource, "coefficient": 1}])
		self.assertEqual(asm.components[0].rate, 500)
		self.assertEqual(asm.components[0].uom, self.uom)

		frappe.db.set_value("Construction Rate Master", resource, "current_rate", 800)
		asm.save(ignore_permissions=True)
		self.assertEqual(asm.components[0].rate, 800)
		self.assertEqual(asm.rate_per_unit, 800)

	def test_component_amount_is_qty_times_rate(self):
		# EST-003 — a component's amount is always coefficient x rate.
		resource = self._make_rate(250)
		asm = self._make_assembly([{"resource": resource, "coefficient": 4}])
		self.assertEqual(asm.components[0].amount, 1000)

	def test_duplicate_assembly_code_rejected(self):
		# EST-005 — assembly_code is the record's name (autoname by field) and
		# unique=1; a second Assembly reusing it is rejected.
		asm = self._make_assembly([])  # random ASM-<hash> code
		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{
					"doctype": "Assembly",
					"assembly_code": asm.assembly_code,
					"assembly_name": "Dup",
					"uom": self.uom,
				}
			).insert(ignore_permissions=True)

	def test_edit_component_coefficient_recomputes_assembly_rate(self):
		# EST-006 — changing a component's coefficient and saving recomputes
		# both that component's amount and the assembly's rate_per_unit.
		resource = self._make_rate(100)
		asm = self._make_assembly([{"resource": resource, "coefficient": 2}])
		self.assertEqual(asm.rate_per_unit, 200)

		asm.components[0].coefficient = 5
		asm.save(ignore_permissions=True)
		self.assertEqual(asm.components[0].amount, 500)
		self.assertEqual(asm.rate_per_unit, 500)

	def test_remove_component_recomputes_assembly_rate(self):
		# EST-007 — removing one of several components (not down to zero)
		# recomputes rate_per_unit to just the remaining components' total.
		r1 = self._make_rate(100)
		r2 = self._make_rate(300)
		asm = self._make_assembly(
			[{"resource": r1, "coefficient": 1}, {"resource": r2, "coefficient": 1}]
		)
		self.assertEqual(asm.rate_per_unit, 400)

		asm.components = [c for c in asm.components if c.resource != r2]
		asm.save(ignore_permissions=True)
		self.assertEqual(len(asm.components), 1)
		self.assertEqual(asm.rate_per_unit, 100)
		self.assertEqual(asm.component_count, 1)

	def test_delete_assembly(self):
		# An unreferenced Assembly deletes cleanly.
		asm = self._make_assembly([])
		frappe.delete_doc("Assembly", asm.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Assembly", asm.name))

	def test_assembly_referenced_by_boq_item_is_link_protected(self):
		# An Assembly linked from a BOQ Item can't be deleted while that link
		# exists (Frappe link integrity) — it must be disabled instead.
		resource = self._make_rate(100)
		asm = self._make_assembly([{"resource": resource, "coefficient": 1}])
		p = self._make_project(company=self.company)
		b = frappe.get_doc(
			{"doctype": "BOQ", "project": p.name, "title": "x", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)
		g = frappe.get_doc(
			{"doctype": "BOQ Group", "boq": b.name, "code": "A", "group_name": "g"}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": b.name,
				"boq_group": g.name,
				"code": "A.1",
				"description": "x",
				"unit": self.uom,
				"planned_qty": 1,
				"rate": 1,
				"assembly": asm.name,
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Assembly", asm.name, ignore_permissions=True)
