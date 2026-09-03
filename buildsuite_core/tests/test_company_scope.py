# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Multi-company isolation: `company` is anchored to the project, and a company-scoped
record from one company cannot be attached to another company's project/document — the
core cross-company guardrail (e.g. one company's BOQ on another company's scope change)."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestCompanyScope(BuildSuiteTestCase):
	def _project(self, company):
		h = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {h}",
				"custom_project_id": f"UAT-{h}",
				"project_status": "Ongoing",
				"company": company,
			}
		).insert(ignore_permissions=True)

	def _boq(self, project):
		return frappe.get_doc(
			{"doctype": "BOQ", "project": project, "title": "X", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)

	def _sco(self, project, **kw):
		return frappe.get_doc(
			{"doctype": "Scope Change Order", "project": project, "title": "X", "reason": "UAT", **kw}
		).insert(ignore_permissions=True)

	def _second_company(self):
		for name in ("XCorp", "XCorp (Demo)", "Parent Group Company India", "_Test Company 3"):
			if name != self.company and frappe.db.exists("Company", name):
				return name
		self.skipTest("needs a second company for the cross-company scenario")

	def test_boq_company_anchored_to_project(self):
		"""A BOQ inherits its project's company (always re-derived, never user-set)."""
		p = self._project(self.company)
		self.assertEqual(self._boq(p.name).company, self.company)

	def test_sco_accepts_same_company_boq(self):
		"""A BOQ revision from the SAME company's project is accepted."""
		p = self._project(self.company)
		boq = self._boq(p.name)
		sco = self._sco(p.name, boq_revision=boq.name)
		self.assertEqual(sco.company, self.company)

	def test_sco_rejects_cross_company_boq(self):
		"""A company-A BOQ cannot be the boq_revision of a company-B project's SCO."""
		c2 = self._second_company()
		pa = self._project(self.company)
		pb = self._project(c2)
		boq_a = self._boq(pa.name)  # belongs to company A
		with self.assertRaises(frappe.ValidationError):
			self._sco(pb.name, boq_revision=boq_a.name)

	# --- per-company masters in a BOQ ------------------------------------
	def _assembly(self, company):
		h = frappe.generate_hash(length=5)
		return frappe.get_doc(
			{
				"doctype": "Assembly",
				"assembly_code": f"ASM-{h}",
				"assembly_name": "X",
				"uom": "Nos",
				"company": company,
			}
		).insert(ignore_permissions=True)

	def _boq_group(self, boq):
		return frappe.get_doc(
			{"doctype": "BOQ Group", "boq": boq, "code": "A", "group_name": "X"}
		).insert(ignore_permissions=True)

	def _boq_item(self, boq, group, **kw):
		return frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": boq,
				"boq_group": group,
				"code": f"A.{frappe.generate_hash(length=3)}",
				"description": "x",
				"unit": "Nos",
				"planned_qty": 1,
				"rate": 1,
				**kw,
			}
		).insert(ignore_permissions=True)

	def test_boq_item_accepts_same_company_assembly(self):
		p = self._project(self.company)
		boq = self._boq(p.name)
		g = self._boq_group(boq.name)
		asm = self._assembly(self.company)
		item = self._boq_item(boq.name, g.name, assembly=asm.name)
		self.assertTrue(item.name)

	def test_boq_item_rejects_cross_company_assembly(self):
		"""A company-A BOQ item cannot pull a company-B Assembly (a per-company master)."""
		c2 = self._second_company()
		p = self._project(self.company)  # BOQ in company A
		boq = self._boq(p.name)
		g = self._boq_group(boq.name)
		asm_b = self._assembly(c2)  # Assembly in company B
		with self.assertRaises(frappe.ValidationError):
			self._boq_item(boq.name, g.name, assembly=asm_b.name)
