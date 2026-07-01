# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Hierarchy date-boundary validation: a child's schedule must sit within its
parent project's expected dates, sub-projects within their parent, and end >= start."""

import frappe
from frappe.utils import add_days

from buildsuite_core.tests.base import BuildSuiteTestCase

P_START = "2026-03-01"
P_END = "2026-09-30"


class TestDateBounds(BuildSuiteTestCase):
	def _dated_project(self, start=P_START, end=P_END, parent=None):
		h = frappe.generate_hash(length=5)
		doc = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT Dates {h}",
				"custom_project_id": f"UAT-D-{h}",
				"project_status": "Ongoing",
				"company": self.company,
				"parent_project": parent,
				"expected_start_date": start,
				"expected_end_date": end,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _new_task(self, project, start, end):
		return frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"UAT {frappe.generate_hash(length=4)}",
				"project": project,
				"exp_start_date": start,
				"exp_end_date": end,
			}
		)

	# --- Task ------------------------------------------------------------
	def test_task_within_project_passes(self):
		p = self._dated_project()
		self._new_task(p.name, P_START, P_END).insert(ignore_permissions=True)  # no throw

	def test_task_start_before_project_rejected(self):
		p = self._dated_project()
		with self.assertRaises(frappe.ValidationError):
			self._new_task(p.name, add_days(P_START, -3), P_END).insert(ignore_permissions=True)

	def test_task_end_after_project_rejected(self):
		p = self._dated_project()
		with self.assertRaises(frappe.ValidationError):
			self._new_task(p.name, P_START, add_days(P_END, 5)).insert(ignore_permissions=True)

	def test_task_end_before_start_rejected(self):
		p = self._dated_project()
		with self.assertRaises(frappe.ValidationError):
			self._new_task(p.name, P_END, P_START).insert(ignore_permissions=True)

	def test_task_unbounded_project_allows_any_dates(self):
		# A project without expected dates imposes no bounds.
		p = self._dated_project(start=None, end=None)
		self._new_task(p.name, P_START, P_END).insert(ignore_permissions=True)  # no throw

	# --- Work Package ----------------------------------------------------
	def test_work_package_out_of_bounds_rejected(self):
		p = self._dated_project()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Work Package",
					"project": p.name,
					"work_package_name": "UAT WP",
					"code": f"WP-{self._n}",
					"start_date": add_days(P_START, -1),
					"end_date": P_END,
				}
			).insert(ignore_permissions=True)

	# --- Stage Planning --------------------------------------------------
	def test_stage_planning_out_of_bounds_rejected(self):
		p = self._dated_project()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Stage Planning",
					"project": p.name,
					"stage_name": "UAT Stage",
					"planned_start": P_START,
					"planned_end": add_days(P_END, 5),
				}
			).insert(ignore_permissions=True)

	# --- Sub-project -----------------------------------------------------
	def test_subproject_within_parent_passes(self):
		parent = self._dated_project()
		self._dated_project(start=P_START, end=P_END, parent=parent.name)  # no throw

	def test_subproject_out_of_parent_bounds_rejected(self):
		parent = self._dated_project()
		with self.assertRaises(frappe.ValidationError):
			self._dated_project(start=add_days(P_START, -10), end=P_END, parent=parent.name)
