# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""BOQ: totals roll-up, cascade delete, sub-item rate snapshot, Assembly explosion,
revisions, approve-supersede and actuals recompute."""

import frappe

from buildsuite_core.api import boq as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestBOQ(BuildSuiteTestCase):
	def _boq(self, project):
		return frappe.get_doc(
			{"doctype": "BOQ", "project": project, "title": "UAT BOQ", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)

	def _group(self, boq):
		return frappe.get_doc(
			{"doctype": "BOQ Group", "boq": boq, "code": "A", "group_name": "Civil"}
		).insert(ignore_permissions=True)

	def _item(self, boq, group, qty, rate, **kw):
		return frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": boq,
				"boq_group": group,
				"code": kw.pop("code", f"A.{frappe.generate_hash(length=3)}"),
				"description": "x",
				"unit": "Nos",
				"planned_qty": qty,
				"rate": rate,
				**kw,
			}
		).insert(ignore_permissions=True)

	def _rate_master(self, rate=100):
		h = frappe.generate_hash(length=5)
		return frappe.get_doc(
			{
				"doctype": "Construction Rate Master",
				"rate_code": f"ZZ-{h}",
				"rate_name": "Z",
				"category": "Material",
				"uom": "Nos",
				"current_rate": rate,
			}
		).insert(ignore_permissions=True)

	# --- roll-up + cascade ----------------------------------------------
	def test_totals_rollup(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		self._item(b.name, g.name, 10, 100)  # 1000
		self._item(b.name, g.name, 5, 200)  # 1000
		b.reload()
		self.assertEqual(b.planned_amount, 2000)
		self.assertEqual(b.margin_amount, 200)
		self.assertEqual(b.tax_amount, 396)  # (2000+200)*18%
		self.assertEqual(b.total, 2596)
		self.assertTrue(b.wp_summaries)
		self.assertAlmostEqual(sum(r.total for r in b.wp_summaries), 2596, places=2)

	# --- project-scope guard on Task / Work Package links ----------------
	def _other_project(self):
		# A second project with a distinct name (base `_make_project` reuses one
		# hash per test, which would collide on the unique project_name).
		h = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {h}",
				"custom_project_id": f"UAT-{h}",
				"project_status": "Ongoing",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

	def _work_package(self, project, name="WP"):
		return frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": project,
				"work_package_name": name,
				"code": f"{name}-{frappe.generate_hash(length=4)}",
			}
		).insert(ignore_permissions=True)

	def test_item_rejects_cross_project_work_package(self):
		# A BOQ Item may only tag a Work Package from the BOQ's own project.
		pa = self._make_project(company=self.company)
		pb = self._other_project()
		b = self._boq(pa.name)
		g = self._group(b.name)
		with self.assertRaises(frappe.ValidationError):
			self._item(b.name, g.name, 1, 1, work_package=self._work_package(pb.name).name)
		# same-project Work Package is accepted
		self._item(b.name, g.name, 1, 1, work_package=self._work_package(pa.name).name)

	def test_item_rejects_cross_project_task(self):
		# A BOQ Item may only link a Task from the BOQ's own project.
		pa = self._make_project(company=self.company)
		pb = self._other_project()
		b = self._boq(pa.name)
		g = self._group(b.name)
		with self.assertRaises(frappe.ValidationError):
			self._item(b.name, g.name, 1, 1, task=self._make_task(pb.name).name)
		# same-project Task is accepted
		self._item(b.name, g.name, 1, 1, task=self._make_task(pa.name).name)

	def test_cascade_delete(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		it = self._item(b.name, g.name, 1, 1)
		frappe.get_doc(
			{
				"doctype": "BOQ Sub Item",
				"boq": b.name,
				"boq_item": it.name,
				"description": "s",
				"qty_per_unit": 1,
			}
		).insert(ignore_permissions=True)
		frappe.delete_doc("BOQ", b.name, force=True, ignore_permissions=True)
		self.assertEqual(frappe.db.count("BOQ Group", {"boq": b.name}), 0)
		self.assertEqual(frappe.db.count("BOQ Item", {"boq": b.name}), 0)
		self.assertEqual(frappe.db.count("BOQ Sub Item", {"boq": b.name}), 0)

	def test_subitem_rate_snapshot(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		it = self._item(b.name, g.name, 1, 1)
		rm = self._rate_master(rate=750)
		si = frappe.get_doc(
			{
				"doctype": "BOQ Sub Item",
				"boq": b.name,
				"boq_item": it.name,
				"rate_master": rm.name,
				"description": "s",
				"qty_per_unit": 2,
			}
		).insert(ignore_permissions=True)
		si.reload()
		self.assertEqual(si.rate, 750)
		self.assertEqual(si.amount, 1500)

	# --- explosion ------------------------------------------------------
	def test_explode_item(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		rm = self._rate_master(rate=100)
		asm = frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"ZZA-{frappe.generate_hash(length=4)}",
				"assembly_name": "A",
				"uom": "Nos",
				"components": [{"resource": rm.name, "coefficient": 3}],
			}
		).insert(ignore_permissions=True)
		it = self._item(b.name, g.name, 4, 0, assembly=asm.name, driving_qty=4)
		api.explode_item(it.name)
		it.reload()
		self.assertEqual(it.quantity_source, "Assembly")
		self.assertEqual(it.rate, asm.rate_per_unit)  # 3*100 = 300
		subs = frappe.get_all("BOQ Sub Item", filters={"boq_item": it.name}, fields=["qty", "qty_per_unit"])
		self.assertEqual(len(subs), 1)
		self.assertEqual(subs[0].qty, 12)  # 3 * 4
		# idempotent
		api.explode_item(it.name)
		self.assertEqual(frappe.db.count("BOQ Sub Item", {"boq_item": it.name}), 1)

	# --- revisions + workflow ------------------------------------------
	def test_create_revision_clones_tree(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		self._item(b.name, g.name, 2, 50)
		new = api.create_revision(b.name)
		nb = frappe.get_doc("BOQ", new)
		self.assertEqual(nb.revision, b.revision + 1)
		self.assertEqual(nb.base_revision, b.name)
		self.assertEqual(nb.status, "Draft")
		self.assertEqual(frappe.db.count("BOQ Item", {"boq": new}), 1)
		self.assertEqual(nb.planned_amount, 100)

	def test_approve_supersedes_sibling(self):
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		api.submit_boq(b.name)
		api.approve_boq(b.name)
		new = api.create_revision(b.name)
		api.submit_boq(new)
		api.approve_boq(new)
		self.assertEqual(frappe.db.get_value("BOQ", b.name, "status"), "Superseded")
		self.assertEqual(frappe.db.get_value("BOQ", new, "status"), "Approved")

	# --- actuals --------------------------------------------------------
	def test_recalculate_actuals_from_task(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)  # task progress -> 40
		b = self._boq(p.name)
		g = self._group(b.name)
		self._item(b.name, g.name, 10, 100, task=t.name)  # planned 1000
		api.recalculate_actuals(b.name)
		b.reload()
		self.assertEqual(b.actual_amount, 400)  # 10 * 40% * 100
