# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Shared base test case + record builders for BuildSuite Core tests.

IMPORTANT: UnitTestCase does NOT roll back the DB (it's for pure in-memory unit
tests). On its own it let every record these tests create COMMIT and persist —
which silently leaked thousands of test Projects/Users into the site. We register
a per-test frappe.db.rollback() cleanup here so records never persist, without
pulling in IntegrationTestCase's heavy test-record fixtures. Subclass
BuildSuiteTestCase in the per-doctype / per-area test modules.
"""

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import today


def get_default_company():
	return frappe.db.get_value("Company", {}, "name")


class BuildSuiteTestCase(UnitTestCase):
	def setUp(self):
		# set_user is session state, not DB — a prior test's leaked frappe.set_user()
		# would otherwise bleed into this one (its user may since be rolled back).
		frappe.set_user("Administrator")
		# Roll back everything this test writes when it finishes (LIFO cleanup).
		self.addCleanup(frappe.db.rollback)
		self.company = get_default_company()
		self._n = frappe.generate_hash(length=6)

	# --- record builders -------------------------------------------------
	def _make_project(self, status="Ongoing", parent=None, company=None):
		doc = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {self._n}",
				"custom_project_id": f"UAT-{self._n}",
				"project_status": status,
				"parent_project": parent,
				"company": company,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _make_task(self, project, task_status="Yet To Start"):
		doc = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"UAT Task {frappe.generate_hash(length=4)}",
				"project": project,
				"task_status": task_status,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _file_tpe(self, task, pct, blocker=0, blocker_detail=None):
		doc = frappe.get_doc(
			{
				"doctype": "Task Progress Entry",
				"task": task,
				"entry_date": today(),
				"cumulative_progress": pct,
				"blocker": blocker,
				"blocker_detail": blocker_detail,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _make_rate_master(self, rate=100, category="Material", uom="Nos"):
		doc = frappe.get_doc(
			{
				"doctype": "Construction Rate Master",
				"rate_code": f"UAT-{frappe.generate_hash(length=5)}",
				"rate_name": "UAT Rate",
				"category": category,
				"uom": uom,
				"current_rate": rate,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc
