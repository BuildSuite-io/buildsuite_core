# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Full day hours: project -> company -> default, validation, and who may set the project's."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.full_day import DEFAULT_FULL_DAY_HOURS, get_full_day_hours

RULE = "Full day hours must be more than 0 and no more than 24."


class TestFullDay(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.project = self._make_project()
		# The company the project actually landed in (what the helper resolves from the project).
		self.company = frappe.db.get_value("Project", self.project.name, "company")

	# --- helpers ---------------------------------------------------------
	def _company_hours(self, hours):
		frappe.db.set_value("Company", self.company, "full_day_hours", hours)

	def _project_hours(self, hours):
		frappe.db.set_value("Project", self.project.name, "full_day_hours", hours)

	def _user(self, *roles):
		email = f"fd-{frappe.generate_hash(length=6)}@example.com"
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "FD", "send_welcome_email": 0}
		)
		user.insert(ignore_permissions=True)
		for role in roles:
			user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		return email

	def _save_project_as(self, user, hours):
		frappe.set_user(user)
		doc = frappe.get_doc("Project", self.project.name)
		doc.flags.ignore_permissions = True  # DocPerm is not what is under test
		doc.full_day_hours = hours
		doc.save()

	# --- the helper ------------------------------------------------------
	def test_company_value_applies_when_project_is_blank(self):
		self._company_hours(9)
		self._project_hours(0)
		self.assertEqual(get_full_day_hours(self.project.name, self.company), 9)

	def test_project_value_wins(self):
		self._company_hours(9)
		self._project_hours(10)
		self.assertEqual(get_full_day_hours(self.project.name, self.company), 10)

	def test_company_is_taken_from_the_project_when_not_given(self):
		self._company_hours(9)
		self._project_hours(0)
		self.assertEqual(get_full_day_hours(self.project.name), 9)

	def test_falls_back_to_the_default_with_nothing_set(self):
		self.assertEqual(get_full_day_hours(), DEFAULT_FULL_DAY_HOURS)
		self.assertEqual(DEFAULT_FULL_DAY_HOURS, 8)

	# --- validation ------------------------------------------------------
	def test_company_refuses_zero_over_24_and_blank(self):
		for bad in (0, 25, -1):
			doc = frappe.get_doc("Company", self.company)
			doc.full_day_hours = bad
			with self.assertRaisesRegex(frappe.ValidationError, RULE):
				doc.save()
		doc = frappe.get_doc("Company", self.company)
		doc.full_day_hours = None
		with self.assertRaises(frappe.MandatoryError):
			doc.save()

	def test_company_accepts_a_valid_value(self):
		doc = frappe.get_doc("Company", self.company)
		doc.full_day_hours = 9.5
		doc.save()
		self.assertEqual(get_full_day_hours(company=self.company), 9.5)

	def test_project_refuses_zero_and_over_24_but_allows_blank(self):
		for bad in (25, -1):
			with self.assertRaisesRegex(frappe.ValidationError, RULE):
				self._save_project_as("Administrator", bad)
		self._save_project_as("Administrator", None)  # blank = use the company's
		self.assertEqual(
			get_full_day_hours(self.project.name, self.company), get_full_day_hours(company=self.company)
		)

	# --- who may set the project's value ---------------------------------
	def test_admins_and_the_projects_own_pm_can_set_it(self):
		pm = self._user("BuildSuite PM")
		frappe.db.set_value("Project", self.project.name, "project_manager", pm)
		for user in (self._user("System Manager"), self._user("BuildSuite Administrator"), pm):
			self._save_project_as(user, 10)
			self.assertEqual(frappe.db.get_value("Project", self.project.name, "full_day_hours"), 10)
			self._project_hours(0)

	def test_anyone_else_is_refused_including_another_projects_pm(self):
		pm = self._user("BuildSuite PM")
		frappe.db.set_value("Project", self.project.name, "project_manager", pm)
		other_pm = self._user("BuildSuite PM")  # a PM, but not of this project
		for user in (other_pm, self._user("BuildSuite Accountant"), self._user("BuildSuite Site Engineer")):
			with self.assertRaises(frappe.PermissionError):
				self._save_project_as(user, 10)
		self.assertFalse(frappe.db.get_value("Project", self.project.name, "full_day_hours"))  # still blank

	def test_unrelated_edits_by_a_non_pm_are_unaffected(self):
		other = self._user("BuildSuite Accountant")
		frappe.set_user(other)
		doc = frappe.get_doc("Project", self.project.name)
		doc.flags.ignore_permissions = True
		doc.notes = "touched"
		doc.save()  # full_day_hours unchanged -> no refusal

	# --- the Company field is permlevel-protected -------------------------
	def test_company_field_is_protected_by_permlevel(self):
		# A role with Company write at level 0 but no level-1 grant can save the company, but its
		# change to the protected field is dropped. System Manager holds the grant, so it sticks.
		for role, sticks in (("System Manager", True), ("HR Manager", False)):
			self._company_hours(8)
			frappe.set_user(self._user(role))
			doc = frappe.get_doc("Company", self.company)
			doc.full_day_hours = 11
			doc.save()
			frappe.set_user("Administrator")
			self.assertEqual(get_full_day_hours(company=self.company), 11 if sticks else 8, role)

	def test_administrator_endpoint_sets_it_and_others_cannot(self):
		from buildsuite_core.api.company import set_full_day_hours

		self._company_hours(8)
		frappe.set_user(self._user("BuildSuite Administrator"))
		set_full_day_hours(self.company, 9)
		self.assertEqual(get_full_day_hours(company=self.company), 9)
		with self.assertRaisesRegex(frappe.ValidationError, RULE):
			set_full_day_hours(self.company, 25)
		frappe.set_user(self._user("BuildSuite Accountant"))
		with self.assertRaises(frappe.PermissionError):
			set_full_day_hours(self.company, 10)
		frappe.set_user("Administrator")
		self.assertEqual(get_full_day_hours(company=self.company), 9)
