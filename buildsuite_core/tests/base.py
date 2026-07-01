# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Shared base test case + record builders for BuildSuite Core unit tests.

UnitTestCase wraps every test in a transaction and rolls it back, so records
created via these helpers never persist. Subclass BuildSuiteTestCase in the
per-doctype / per-area test modules.
"""

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import today


def get_default_company():
	return frappe.db.get_value("Company", {}, "name")


class BuildSuiteTestCase(UnitTestCase):
	def setUp(self):
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
