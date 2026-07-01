# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for BuildSuite Project customisations: status sync, company inherit/lock,
progress rollup, cascade delete, and team membership (incl. the PRM-002 PM
auto-membership and the FLIP visibility model)."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestProject(BuildSuiteTestCase):
	# --- project_status <-> native status (PRJ-008, PRJ-009) ------------
	def test_project_status_syncs_to_native(self):
		p = self._make_project(status="Ongoing", company=self.company)
		self.assertEqual(p.project_status, "Ongoing")
		self.assertEqual(p.status, "Open")

		p.project_status = "Completed"
		p.save(ignore_permissions=True)
		self.assertEqual(p.status, "Completed")

	def test_project_status_defaults_to_new(self):
		p = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT {self._n}",
				"custom_project_id": f"UAT-{self._n}",
				"company": self.company,
			}
		)
		p.insert(ignore_permissions=True)
		self.assertEqual(p.project_status, "New")
		self.assertEqual(p.status, "Open")

	# --- company inherit + lock (PRJ-005, PRJ-012, PRJ-013) -------------
	def test_subproject_inherits_company(self):
		parent = self._make_project(company=self.company)
		child = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT sub {self._n}",
				"custom_project_id": f"UAT-SUB-{self._n}",
				"parent_project": parent.name,
				"is_group": 0,
			}
		)
		child.insert(ignore_permissions=True)
		self.assertEqual(child.company, self.company)

	def test_project_infers_company_from_creating_user(self):
		frappe.db.set_value("User", frappe.session.user, "company", self.company)
		p = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT infer {self._n}",
				"custom_project_id": f"UAT-INF-{self._n}",
			}
		)
		p.insert(ignore_permissions=True)
		self.assertEqual(p.company, self.company)

	def test_company_locked_after_create(self):
		others = frappe.get_all("Company", filters={"name": ("!=", self.company)}, pluck="name")
		p = self._make_project(company=self.company)
		if others:
			p.company = others[0]
			p.save(ignore_permissions=True)
			self.assertEqual(p.company, self.company)

	# --- progress rollup (PRJ-010) --------------------------------------
	def test_project_progress_rolls_up(self):
		p = self._make_project(company=self.company)
		t1 = self._make_task(p.name)
		t2 = self._make_task(p.name)
		self._file_tpe(t1.name, 100)
		self._file_tpe(t2.name, 50)
		p.reload()
		self.assertEqual(p.percent_complete, 75)

	def test_project_progress_rounded_to_whole_number(self):
		p = self._make_project(company=self.company)
		for pct in (33, 33, 34):
			self._file_tpe(self._make_task(p.name).name, pct)
		p.reload()
		self.assertEqual(p.percent_complete, round(p.percent_complete))
		self.assertEqual(p.percent_complete, 33)

	def test_parent_progress_weighted_by_subproject_task_count(self):
		parent = self._make_project(company=self.company)
		parent.is_group = 1
		parent.save(ignore_permissions=True)

		pt = self._make_task(parent.name)
		self._file_tpe(pt.name, 60)

		sub = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT sub {self._n}",
				"custom_project_id": f"UAT-SUB-{self._n}",
				"parent_project": parent.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		for _ in range(3):
			self._file_tpe(self._make_task(sub.name).name, 100)

		sub.reload()
		self.assertEqual(sub.percent_complete, 100)
		# (60*1 + 100*3) / (1 + 3) = 90
		parent.reload()
		self.assertEqual(parent.percent_complete, 90)

	# --- required + unique fields (PRJ-003, PRJ-018) --------------------
	def test_duplicate_project_id_rejected(self):
		# PRJ-003: custom_project_id is unique — a second project reusing it fails.
		self._make_project(company=self.company)  # custom_project_id = UAT-<n>
		dup = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"UAT dup {self._n}",
				"custom_project_id": f"UAT-{self._n}",  # same id
				"company": self.company,
			}
		)
		with self.assertRaises(frappe.exceptions.ValidationError):
			dup.insert(ignore_permissions=True)

	def test_project_requires_name(self):
		# PRJ-018: project_name is mandatory.
		p = frappe.get_doc(
			{
				"doctype": "Project",
				"custom_project_id": f"UAT-NONAME-{self._n}",
				"company": self.company,
			}
		)
		with self.assertRaises(frappe.MandatoryError):
			p.insert(ignore_permissions=True)

	# --- guarded cascade delete (PRJ-014, STG-011) ----------------------
	def test_cascade_delete_removes_descendants(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 20)
		wp = frappe.get_doc(
			{
				"doctype": "Work Package",
				"project": p.name,
				"work_package_name": "UAT WP",
				"code": f"WP-{self._n}",
			}
		).insert(ignore_permissions=True)
		stage = frappe.get_doc(
			{
				"doctype": "Stage Planning",
				"stage_name": f"CASC {self._n}",
				"project": p.name,
				"workflow_state": "Draft",
			}
		).insert(ignore_permissions=True)

		frappe.delete_doc("Project", p.name, ignore_permissions=True)

		self.assertFalse(frappe.db.exists("Project", p.name))
		self.assertFalse(frappe.db.exists("Task", t.name))
		self.assertFalse(frappe.db.exists("Task Progress Entry", tpe.name))
		self.assertFalse(frappe.db.exists("Work Package", wp.name))
		self.assertFalse(frappe.db.exists("Stage Planning", stage.name))

	# --- team membership (custom_team_members) --------------------------
	def test_project_team_add_and_remove(self):
		from buildsuite_core.api.project_team import (
			add_project_team_member,
			remove_project_team_member,
		)

		p = self._make_project(company=self.company)

		team = add_project_team_member(p.name, "Administrator")
		self.assertTrue(any(m["user"] == "Administrator" for m in team))

		# Idempotent — adding again doesn't duplicate.
		team = add_project_team_member(p.name, "Administrator")
		self.assertEqual(len([m for m in team if m["user"] == "Administrator"]), 1)

		team = remove_project_team_member(p.name, "Administrator")
		self.assertFalse(any(m["user"] == "Administrator" for m in team))

	def test_project_manager_auto_added_to_team(self):
		# PRM-002 — the assigned project_manager is auto-added to the team so the
		# team-scoped visibility model surfaces the project for them.
		pm = f"pm-{self._n}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": pm,
				"first_name": "PM",
				"send_welcome_email": 0,
				"user_type": "System User",
				"persona": "Project Manager",
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		p = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"PMTEAM {self._n}",
				"custom_project_id": f"PMTEAM-{self._n}",
				"project_status": "Ongoing",
				"company": self.company,
				"project_manager": pm,
			}
		).insert(ignore_permissions=True)
		self.assertTrue(
			frappe.db.exists(
				"Project Team",
				{
					"parent": p.name,
					"parentfield": "custom_team_members",
					"user": pm,
				},
			)
		)
