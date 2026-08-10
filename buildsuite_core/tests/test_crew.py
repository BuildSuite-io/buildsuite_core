# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Crew save API + the controller's member rules."""

import frappe

from buildsuite_core.api.crew import save_crew
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestCrew(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.trade = self._trade()
		self.worker_a = self._worker(900)
		self.worker_b = self._worker(1100)

	def _trade(self):
		name = f"Trade {frappe.generate_hash(length=4)}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": name}).insert(ignore_permissions=True)
		return name

	def _worker(self, wage):
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"naming_series": "HR-EMP-",
				"first_name": f"UAT {frappe.generate_hash(length=4)}",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"company": self.company,
				"is_labour": 1,
				"custom_trade": self.trade,
				"custom_wage": wage,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _save(self, members=None, **kwargs):
		payload = {"crew_name": "Block A Gang", "company": self.company}
		payload.update(kwargs)
		if members is not None:
			payload["members"] = frappe.as_json(members)
		return save_crew(**payload)

	def test_members_and_count(self):
		res = self._save([{"field_employee": self.worker_a}, {"field_employee": self.worker_b}])
		doc = frappe.get_doc("Crew", res["name"])
		self.assertEqual([m.field_employee for m in doc.members], [self.worker_a, self.worker_b])
		self.assertEqual(doc.members_count, 2)

	def test_row_fetches_from_the_worker(self):
		row = frappe.get_doc("Crew", self._save([{"field_employee": self.worker_a}])["name"]).members[0]
		self.assertEqual(row.role_in_crew, self.trade)
		self.assertEqual(row.daily_rate, 900)
		self.assertEqual(row.employee_name, frappe.db.get_value("Employee", self.worker_a, "employee_name"))

	def test_hand_set_role_survives_a_resave(self):
		other = self._trade()
		res = self._save([{"field_employee": self.worker_a}])
		self._save([{"field_employee": self.worker_a, "role_in_crew": other}], name=res["name"])
		self.assertEqual(frappe.get_doc("Crew", res["name"]).members[0].role_in_crew, other)

	def test_client_cannot_set_the_daily_rate(self):
		res = self._save([{"field_employee": self.worker_a, "daily_rate": 99999}])
		self.assertEqual(frappe.get_doc("Crew", res["name"]).members[0].daily_rate, 900)

	def test_update_replaces_the_rows(self):
		res = self._save([{"field_employee": self.worker_a}, {"field_employee": self.worker_b}])
		self._save([{"field_employee": self.worker_b}], name=res["name"])
		doc = frappe.get_doc("Crew", res["name"])
		self.assertEqual([m.field_employee for m in doc.members], [self.worker_b])
		self.assertEqual(doc.members_count, 1)

	def test_header_only_save_keeps_the_roster(self):
		# Omitting `members` used to run doc.set("members", []) and delete everyone.
		res = self._save([{"field_employee": self.worker_a}, {"field_employee": self.worker_b}])
		save_crew(name=res["name"], crew_name="Renamed", company=self.company)
		doc = frappe.get_doc("Crew", res["name"])
		self.assertEqual(len(doc.members), 2)
		self.assertEqual(doc.members_count, 2)

	def test_duplicate_member_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "already a member"):
			self._save([{"field_employee": self.worker_a}, {"field_employee": self.worker_a}])

	def test_blank_member_is_rejected(self):
		# Match the message: field_employee is reqd:1, so MandatoryError (itself a
		# ValidationError) would satisfy a bare assertRaises without our check.
		with self.assertRaisesRegex(frappe.ValidationError, "Field Employee is required"):
			self._save([{"field_employee": ""}])

	def test_blank_crew_name_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "required"):
			self._save(crew_name="   ")

	def test_unknown_name_does_not_create_a_duplicate(self):
		with self.assertRaisesRegex(frappe.ValidationError, "no longer exists"):
			self._save(name="CRW-DOES-NOT-EXIST")

	def test_object_payload_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "list of rows"):
			save_crew(crew_name="Bad", company=self.company, members=frappe.as_json({"a": 1}))

	def test_company_falls_back_to_the_default(self):
		from buildsuite_core.utils.project import default_company

		res = save_crew(crew_name="No Company Gang")
		self.assertEqual(frappe.db.get_value("Crew", res["name"], "company"), default_company())
