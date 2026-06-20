# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.tests.base import BuildSuiteTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestWorkPackage(IntegrationTestCase):
	pass


class TestWorkPackage(BuildSuiteTestCase):
	"""Work Package status auto-advances from its tasks' progress, but a manual
	On Hold is respected."""

	def test_wp_status_autoadvances(self):
		p = self._make_project(company=self.company)
		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": p.name,
				"work_package_name": "UAT WP",
				"code": f"WP-{self._n}",
				"status": "Planned",
			}
		).insert(ignore_permissions=True)
		t1 = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": "WP task 1",
				"project": p.name,
				"work_package": wp.name,
				"task_status": "Yet To Start",
			}
		).insert(ignore_permissions=True)
		t2 = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": "WP task 2",
				"project": p.name,
				"work_package": wp.name,
				"task_status": "Yet To Start",
			}
		).insert(ignore_permissions=True)

		# Any task progress → Planned advances to In Progress.
		self._file_tpe(t1.name, 40)
		self.assertEqual(frappe.db.get_value("Work Package", wp.name, "status"), "In Progress")

		# All tasks at 100 → Completed.
		self._file_tpe(t1.name, 100)
		self._file_tpe(t2.name, 100)
		self.assertEqual(frappe.db.get_value("Work Package", wp.name, "status"), "Completed")

	def test_wp_status_on_hold_is_respected(self):
		p = self._make_project(company=self.company)
		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": p.name,
				"work_package_name": "UAT WP hold",
				"code": f"WPH-{self._n}",
				"status": "On Hold",
			}
		).insert(ignore_permissions=True)
		t = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": "held task",
				"project": p.name,
				"work_package": wp.name,
				"task_status": "Yet To Start",
			}
		).insert(ignore_permissions=True)
		self._file_tpe(t.name, 40)  # progress filed, but WP is manually On Hold
		self.assertEqual(frappe.db.get_value("Work Package", wp.name, "status"), "On Hold")

	def test_wp_requires_project(self):
		# WP-002
		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"work_package_name": "no project",
				"code": f"WPNP-{self._n}",
			}
		)
		with self.assertRaises(frappe.MandatoryError):
			wp.insert(ignore_permissions=True)

	def test_empty_wp_deletes(self):
		# A work package with no tasks deletes cleanly.
		p = self._make_project(company=self.company)
		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": p.name,
				"work_package_name": "empty",
				"code": f"WPE-{self._n}",
			}
		).insert(ignore_permissions=True)
		frappe.delete_doc("Work Package", wp.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Work Package", wp.name))

	def test_wp_with_tasks_is_link_protected(self):
		# WP-005 (current behavior): a WP linked by a task can't be deleted while
		# the task still references it (Frappe link integrity).
		p = self._make_project(company=self.company)
		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": p.name,
				"work_package_name": "linked",
				"code": f"WPL-{self._n}",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Task",
				"subject": "linked task",
				"project": p.name,
				"work_package": wp.name,
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Work Package", wp.name, ignore_permissions=True)
