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

	# --- estimate template import + project/WP clone ---------------------
	def test_import_template_into_boq_creates_lines(self):
		# EST-018 — importing an Estimate Template seeds groups + items onto a
		# Draft BOQ: an Assembly row auto-explodes into sub-items, a Resource
		# row gets a single rate-analysis sub-item.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		rm = self._rate_master(rate=150)
		asm = frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"TPL-ASM-{frappe.generate_hash(length=5)}",
				"assembly_name": "Tpl Assembly",
				"uom": "Nos",
				"components": [{"resource": rm.name, "coefficient": 2}],
			}
		).insert(ignore_permissions=True)  # rate_per_unit = 300
		tpl = frappe.get_doc(
			{
				"doctype": "Estimate Template",
				"template_code": f"TPL-{frappe.generate_hash(length=5)}",
				"template_name": "Tpl",
				"rows": [
					{"group_name": "Civil", "line_type": "Assembly", "assembly": asm.name, "placeholder_qty": 4},
					{"group_name": "Civil", "line_type": "Resource", "resource": rm.name, "placeholder_qty": 3},
				],
			}
		).insert(ignore_permissions=True)

		res = api.import_template(b.name, tpl.name)
		self.assertEqual(res["seeded"], 2)
		self.assertEqual(frappe.db.count("BOQ Group", {"boq": b.name}), 1)  # both rows share "Civil"

		items = frappe.get_all(
			"BOQ Item", filters={"boq": b.name}, fields=["name", "assembly", "quantity_source"]
		)
		self.assertEqual(len(items), 2)
		asm_item = next(i for i in items if i.assembly)
		self.assertEqual(asm_item.quantity_source, "Assembly")  # explode_item overwrote "Template"
		self.assertEqual(frappe.db.count("BOQ Sub Item", {"boq_item": asm_item.name}), 1)

		res_item = next(i for i in items if not i.assembly)
		self.assertEqual(res_item.quantity_source, "Template")
		subs = frappe.get_all("BOQ Sub Item", filters={"boq_item": res_item.name}, fields=["rate_master"])
		self.assertEqual(len(subs), 1)
		self.assertEqual(subs[0].rate_master, rm.name)

	def test_clone_estimate_project_to_project(self):
		# EST-019 — cloning to a different project creates a fresh Draft BOQ
		# there; items carry over but with actuals reset (task cleared) and no
		# stale Work Package tag (the target project's WPs don't apply there).
		pa = self._make_project(company=self.company)
		pb = self._other_project()
		b = self._boq(pa.name)
		g = self._group(b.name)
		t = self._make_task(pa.name)
		wp = self._work_package(pa.name)
		self._item(b.name, g.name, 5, 100, task=t.name, work_package=wp.name)

		res = api.clone_boq(from_project=pa.name, to_project=pb.name)
		self.assertEqual(res["mode"], "project-to-project")
		new_boq = res["boq"]
		self.assertNotEqual(new_boq, b.name)
		self.assertEqual(frappe.db.get_value("BOQ", new_boq, "status"), "Draft")

		new_items = frappe.get_all(
			"BOQ Item",
			filters={"boq": new_boq},
			fields=["name", "task", "work_package", "planned_qty", "rate"],
		)
		self.assertEqual(len(new_items), 1)
		ni = new_items[0]
		self.assertIsNone(ni.task)
		self.assertIsNone(ni.work_package)
		self.assertEqual(ni.planned_qty, 5)
		self.assertEqual(ni.rate, 100)

	def test_clone_estimate_wp_to_wp(self):
		# EST-020 — cloning WP->WP within the same project retags a copy of
		# the source WP's lines onto the target WP, inside the SAME BOQ; the
		# original WP's lines are left untouched.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		wp_a = self._work_package(p.name, name="WPA")
		wp_b = self._work_package(p.name, name="WPB")
		self._item(b.name, g.name, 2, 50, work_package=wp_a.name)

		res = api.clone_boq(
			from_project=p.name, to_project=p.name, from_work_package=wp_a.name, to_work_package=wp_b.name
		)
		self.assertEqual(res["mode"], "wp-to-wp")
		self.assertEqual(res["boq"], b.name)
		self.assertEqual(res["cloned"], 1)
		self.assertEqual(frappe.db.count("BOQ Item", {"boq": b.name, "work_package": wp_a.name}), 1)
		self.assertEqual(frappe.db.count("BOQ Item", {"boq": b.name, "work_package": wp_b.name}), 1)

	# --- snapshot vs. re-explode, multi-UOM, manual lines -----------------
	def test_boq_snapshot_immune_to_later_rate_change(self):
		# EST-011 — a BOQ Sub Item's rate is fixed at the moment it's saved from
		# its Rate Master; later changing that resource's rate elsewhere does
		# NOT reach back and alter the already-persisted sub-item.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		it = self._item(b.name, g.name, 1, 1)
		rm = self._rate_master(rate=500)
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
		self.assertEqual(si.rate, 500)
		self.assertEqual(si.amount, 1000)

		frappe.db.set_value("Construction Rate Master", rm.name, "current_rate", 900)
		si.reload()
		self.assertEqual(si.rate, 500)  # unchanged — no automatic re-snapshot
		self.assertEqual(si.amount, 1000)

	def test_reexplode_refreshes_subitems_to_current_rates(self):
		# EST-012 — re-exploding a line after its Assembly definition changed
		# refreshes the sub-items to match the CURRENT assembly, not the stale one.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		rm = self._rate_master(rate=100)
		asm = frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"REX-{frappe.generate_hash(length=4)}",
				"assembly_name": "Rex",
				"uom": "Nos",
				"components": [{"resource": rm.name, "coefficient": 2}],
			}
		).insert(ignore_permissions=True)  # rate_per_unit = 200
		it = self._item(b.name, g.name, 1, 0, assembly=asm.name, driving_qty=1)
		api.explode_item(it.name)
		self.assertEqual(frappe.db.count("BOQ Sub Item", {"boq_item": it.name}), 1)

		# Assembly definition changes: a second component is added.
		rm2 = self._rate_master(rate=50)
		asm.append("components", {"resource": rm2.name, "coefficient": 3})
		asm.save(ignore_permissions=True)  # rate_per_unit = 200 + 150 = 350

		api.explode_item(it.name)  # re-explode
		it.reload()
		self.assertEqual(it.rate, 350)
		self.assertEqual(frappe.db.count("BOQ Sub Item", {"boq_item": it.name}), 2)

	def test_multi_uom_component_math(self):
		# EST-013 — an Assembly can mix components across different UOMs (Nos and
		# Kg); each explodes and rolls up on its own numbers, independent of the
		# others' unit.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		r_nos = self._rate_master(rate=100)  # uom=Nos
		r_kg = frappe.get_doc(
			{
				"doctype": "Construction Rate Master",
				"rate_code": f"KG-{frappe.generate_hash(length=5)}",
				"rate_name": "Kg resource",
				"category": "Material",
				"uom": "Kg",
				"current_rate": 40,
			}
		).insert(ignore_permissions=True)
		asm = frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"MU-{frappe.generate_hash(length=4)}",
				"assembly_name": "Multi UOM",
				"uom": "Nos",
				"components": [
					{"resource": r_nos.name, "coefficient": 2},  # 200
					{"resource": r_kg.name, "coefficient": 5},  # 200
				],
			}
		).insert(ignore_permissions=True)  # rate_per_unit = 400

		it = self._item(b.name, g.name, 1, 0, assembly=asm.name, driving_qty=1)
		api.explode_item(it.name)
		subs = frappe.get_all(
			"BOQ Sub Item", filters={"boq_item": it.name}, fields=["rate_master", "amount"]
		)
		self.assertEqual(len(subs), 2)
		by_resource = {s.rate_master: s for s in subs}
		self.assertEqual(by_resource[r_nos.name].amount, 200)
		self.assertEqual(by_resource[r_kg.name].amount, 200)
		it.reload()
		self.assertEqual(it.rate, 400)

	def test_manual_boq_line_not_overwritten_by_assembly_logic(self):
		# EST-014 — a line with no Assembly link stays quantity_source=Manual
		# and gets no sub-items auto-created.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)
		g = self._group(b.name)
		it = self._item(b.name, g.name, 5, 100)  # no assembly
		self.assertEqual(it.quantity_source, "Manual")
		self.assertEqual(frappe.db.count("BOQ Sub Item", {"boq_item": it.name}), 0)

	# --- BOQ-level defaults + per-WP summary ------------------------------
	def test_boq_tax_and_margin_defaults_applied(self):
		# EST-029 — a new BOQ defaults margin_rate to 10% and tax_rate to 18%
		# when they aren't explicitly set.
		p = self._make_project(company=self.company)
		b = frappe.get_doc({"doctype": "BOQ", "project": p.name, "title": "Defaults"}).insert(
			ignore_permissions=True
		)
		self.assertEqual(b.margin_rate, 10)
		self.assertEqual(b.tax_rate, 18)

	def test_boq_wp_summary_recomputes(self):
		# EST-032 — wp_summaries splits margin/tax/total proportionally across
		# each Work Package's planned share, and recomputes when a line changes.
		p = self._make_project(company=self.company)
		b = self._boq(p.name)  # margin 10%, tax 18%
		g = self._group(b.name)
		wp_a = self._work_package(p.name, name="WPA")
		wp_b = self._work_package(p.name, name="WPB")
		it_a = self._item(b.name, g.name, 10, 100, work_package=wp_a.name)  # 1000
		self._item(b.name, g.name, 10, 100, work_package=wp_b.name)  # 1000
		b.reload()
		by_wp = {r.work_package: r for r in b.wp_summaries}
		self.assertEqual(by_wp[wp_a.name].planned_amount, 1000)
		self.assertEqual(by_wp[wp_b.name].planned_amount, 1000)
		self.assertAlmostEqual(by_wp[wp_a.name].total, 1298, places=2)  # half of 2596
		self.assertAlmostEqual(by_wp[wp_b.name].total, 1298, places=2)

		# Edit one line's rate -> the WP split recomputes to the new proportions.
		it_a.reload()
		it_a.rate = 300  # WPA planned -> 3000
		it_a.save(ignore_permissions=True)
		b.reload()
		by_wp = {r.work_package: r for r in b.wp_summaries}
		self.assertEqual(by_wp[wp_a.name].planned_amount, 3000)
		self.assertEqual(by_wp[wp_b.name].planned_amount, 1000)
