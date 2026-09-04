# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Field Attendance draft save API + the roster modes."""

import frappe

from buildsuite_core.api.field_attendance import get_roster, save_field_attendance
from buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance import (
	MAX_OT_HOURS_PER_DAY,
)
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestFieldAttendance(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.trade = f"Trade {frappe.generate_hash(length=4)}"
		frappe.get_doc({"doctype": "Labour Trade", "trade": self.trade}).insert(ignore_permissions=True)
		self.project = self._project()
		self.worker_a = self._worker(900)
		self.worker_b = self._worker(1100)
		self.today = frappe.utils.today()

	def _project(self):
		n = frappe.generate_hash(length=6)
		doc = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {n}",
				"custom_project_id": f"UAT-{n}",
				"project_status": "Ongoing",
				"company": self.company,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _worker(self, wage, projects=None):
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
				"custom_wage_for_overtime": 50,
				"custom_project_assigned": [{"project": p} for p in (projects or [])],
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _save(self, workers=None, **kwargs):
		payload = {
			"project": self.project,
			"date": self.today,
			"status": "Present",
			"employee_list": frappe.as_json(
				[{"employee": w, "status": "Present"} for w in (workers or [self.worker_a])]
			),
		}
		payload.update(kwargs)  # a caller may override employee_list wholesale
		return save_field_attendance(**payload)

	def test_create_saves_rows_as_draft(self):
		res = self._save([self.worker_a, self.worker_b])
		self.assertEqual(res["docstatus"], 0)
		self.assertEqual([r["employee"] for r in res["employee_list"]], [self.worker_a, self.worker_b])

	def test_rates_are_stamped_and_not_client_settable(self):
		res = self._save(
			employee_list=frappe.as_json(
				[
					{
						"employee": self.worker_a,
						"status": "Present",
						"labour_rate": 99999,
						"overtime_rate": 88888,
					}
				]
			)
		)
		row = res["employee_list"][0]
		self.assertEqual(row["labour_rate"], 900)
		self.assertEqual(row["overtime_rate"], 50)

	def test_update_replaces_the_rows(self):
		res = self._save([self.worker_a, self.worker_b])
		updated = self._save([self.worker_b], name=res["name"])
		self.assertEqual([r["employee"] for r in updated["employee_list"]], [self.worker_b])

	def test_a_submitted_sheet_cannot_be_edited(self):
		res = self._save()
		frappe.get_doc("Field Attendance", res["name"]).submit()
		with self.assertRaisesRegex(frappe.ValidationError, "draft"):
			self._save([self.worker_b], name=res["name"])

	def test_partial_update_keeps_the_header(self):
		# status defaulted to "Present" and the hours/comments were written
		# unguarded, so a partial update silently revived an Absent sheet.
		res = self._save(status="Absent", overtime_hours=0, comments="Rained off")
		save_field_attendance(
			name=res["name"],
			project=self.project,
			date=self.today,
			employee_list=frappe.as_json([{"employee": self.worker_a, "status": "Absent"}]),
		)
		doc = frappe.get_doc("Field Attendance", res["name"])
		self.assertEqual(doc.status, "Absent")
		self.assertEqual(doc.comments, "Rained off")

	def test_unknown_name_does_not_create_a_duplicate(self):
		with self.assertRaisesRegex(frappe.ValidationError, "no longer exists"):
			self._save(name="HR-FA-2026-99999")

	def test_rejects_empty_list_missing_project_and_duplicates(self):
		with self.assertRaisesRegex(frappe.ValidationError, "at least one"):
			self._save(employee_list=frappe.as_json([]))
		with self.assertRaisesRegex(frappe.ValidationError, "Project is required"):
			self._save(project=None)
		with self.assertRaisesRegex(frappe.ValidationError, "more than once"):
			self._save([self.worker_a, self.worker_a])

	def test_object_payload_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "list of rows"):
			self._save(employee_list=frappe.as_json({"employee": self.worker_a}))

	def test_roster_assigned_reads_project_allocations(self):
		allocated = self._worker(800, projects=[self.project])
		ids = [r["employee"] for r in get_roster(self.project)]
		self.assertIn(allocated, ids)
		self.assertNotIn(self.worker_a, ids)

	def test_roster_normalises_keys(self):
		# get_assigned_employees returns bare ids; the API resolves names.
		for row in get_roster(self.project):
			self.assertIn("employee", row)
			self.assertIn("employee_name", row)

	def _save_with_overtime(self, hours):
		return self._save(
			employee_list=frappe.as_json(
				[{"employee": self.worker_a, "status": "Present", "overtime_hours": hours}]
			)
		)

	def test_overtime_up_to_the_daily_limit_is_allowed(self):
		res = self._save_with_overtime(MAX_OT_HOURS_PER_DAY)
		self.assertEqual(res["employee_list"][0]["overtime_hours"], MAX_OT_HOURS_PER_DAY)

	def test_overtime_over_the_daily_limit_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "daily limit"):
			self._save_with_overtime(MAX_OT_HOURS_PER_DAY + 0.5)

	def test_overtime_at_the_limit_survives_submit(self):
		res = self._save_with_overtime(MAX_OT_HOURS_PER_DAY)
		frappe.get_doc("Field Attendance", res["name"]).submit()

		self.assertEqual(
			frappe.db.get_value(
				"Overtime Attendance Register",
				{"field_attendance": res["name"], "docstatus": 1},
				"overtime_hours",
			),
			MAX_OT_HOURS_PER_DAY,
		)
