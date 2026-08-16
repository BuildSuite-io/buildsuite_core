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



class IntegrationTestMachineryUsage(IntegrationTestCase):
	"""
	Integration tests for MachineryUsage.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestMachineryUsage(BuildSuiteTestCase):
	def _machine(self, rate=500):
		mtype = frappe.get_doc(
			{"doctype": "Machinery Type", "type_name": f"UAT Type {frappe.generate_hash(length=5)}"}
		).insert(ignore_permissions=True)
		return frappe.get_doc(
			{
				"doctype": "Machinery",
				"machinery_name": f"UAT Machine {frappe.generate_hash(length=5)}",
				"machinery_type": mtype.name,
				"company": self.company,
				"rate": rate,
				"rate_unit": "Hour",
			}
		).insert(ignore_permissions=True)

	def _project(self):
		h = frappe.generate_hash(length=6)
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {h}",
				"custom_project_id": f"UAT-{h}",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

	def test_task_must_belong_to_selected_project(self):
		machine = self._machine()
		pa = self._project()
		pb = self._project()
		task_a = self._make_task(pa.name)

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Machinery Usage",
					"machine": machine.name,
					"project": pb.name,
					"task": task_a.name,  # belongs to pa, not pb
					"date": "2026-07-30",
					"quantity": 2,
					"unit": "Hours",
				}
			).insert(ignore_permissions=True)

		# same-project task is accepted
		frappe.get_doc(
			{
				"doctype": "Machinery Usage",
				"machine": machine.name,
				"project": pa.name,
				"task": task_a.name,
				"date": "2026-07-30",
				"quantity": 2,
				"unit": "Hours",
			}
		).insert(ignore_permissions=True)

	def test_task_check_skipped_without_project(self):
		machine = self._machine()
		pa = self._project()
		task_a = self._make_task(pa.name)
		# task set, no project selected -> the cross-project check never fires
		frappe.get_doc(
			{
				"doctype": "Machinery Usage",
				"machine": machine.name,
				"task": task_a.name,
				"date": "2026-07-30",
				"quantity": 2,
				"unit": "Hours",
			}
		).insert(ignore_permissions=True)  # no throw

	def test_rate_fetched_from_machine(self):
		machine = self._machine(rate=750)
		usage = frappe.get_doc(
			{
				"doctype": "Machinery Usage",
				"machine": machine.name,
				"date": "2026-07-30",
				"quantity": 2,
				"unit": "Hours",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(usage.rate, 750)

	def test_date_defaults_to_today(self):
		machine = self._machine()
		usage = frappe.get_doc(
			{"doctype": "Machinery Usage", "machine": machine.name, "quantity": 1, "unit": "Hours"}
		).insert(ignore_permissions=True)
		self.assertEqual(frappe.utils.getdate(usage.date), frappe.utils.getdate())

	def test_unit_defaults_to_first_option(self):
		# `unit` is a Select field with no explicit default — same Frappe
		# quirk as Machinery's ownership/status: it silently becomes "Days"
		# (the first option) rather than staying blank.
		machine = self._machine()
		usage = frappe.get_doc({"doctype": "Machinery Usage", "machine": machine.name, "quantity": 1}).insert(
			ignore_permissions=True
		)
		self.assertEqual(usage.unit, "Days")

	def test_create_machinery_usage_minimal(self):
		# `machine` is the only mandatory field — everything else can be blank.
		machine = self._machine()
		usage = frappe.get_doc({"doctype": "Machinery Usage", "machine": machine.name}).insert(
			ignore_permissions=True
		)
		self.assertTrue(usage.name)

	def test_machinery_usage_missing_machine_rejected(self):
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc({"doctype": "Machinery Usage", "quantity": 1, "unit": "Hours"}).insert(
				ignore_permissions=True
			)

	def test_update_and_delete_machinery_usage(self):
		machine = self._machine()
		usage = frappe.get_doc(
			{
				"doctype": "Machinery Usage",
				"machine": machine.name,
				"quantity": 2,
				"unit": "Hours",
				"fuel_cost": 50,
			}
		).insert(ignore_permissions=True)

		usage.quantity = 5
		usage.fuel_cost = 100
		usage.save(ignore_permissions=True)
		usage.reload()
		self.assertEqual(usage.quantity, 5)
		self.assertEqual(usage.fuel_cost, 100)

		frappe.delete_doc("Machinery Usage", usage.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Machinery Usage", usage.name))
