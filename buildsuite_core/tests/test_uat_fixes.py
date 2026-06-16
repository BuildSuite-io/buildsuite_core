# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Regression tests for the M1 UAT failure fixes.

Each test maps to one or more UAT cases (referenced in the test name/docstring).
UnitTestCase wraps every test in a transaction and rolls it back, so the records
created here never persist.
"""

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import today


def _company():
	return frappe.db.get_value("Company", {}, "name")


class TestUATFixes(UnitTestCase):
	def setUp(self):
		self.company = _company()
		self._n = frappe.generate_hash(length=6)

	# --- helpers ---------------------------------------------------------
	def _make_project(self, status="Ongoing", parent=None, company=None):
		doc = frappe.get_doc({
			"doctype": "Project",
			"project_name": f"UAT {self._n}",
			"custom_project_id": f"UAT-{self._n}",
			"project_status": status,
			"parent_project": parent,
			"company": company,
		})
		doc.insert(ignore_permissions=True)
		return doc

	def _make_task(self, project, task_status="Yet To Start"):
		doc = frappe.get_doc({
			"doctype": "Task",
			"subject": f"UAT Task {frappe.generate_hash(length=4)}",
			"project": project,
			"task_status": task_status,
		})
		doc.insert(ignore_permissions=True)
		return doc

	def _file_tpe(self, task, pct, blocker=0, blocker_detail=None):
		doc = frappe.get_doc({
			"doctype": "Task Progress Entry",
			"task": task,
			"entry_date": today(),
			"cumulative_progress": pct,
			"blocker": blocker,
			"blocker_detail": blocker_detail,
		})
		doc.insert(ignore_permissions=True)
		return doc

	# --- C: project status sync (PRJ-008, PRJ-009) ----------------------
	def test_project_status_syncs_to_native(self):
		p = self._make_project(status="Ongoing", company=self.company)
		self.assertEqual(p.project_status, "Ongoing")
		self.assertEqual(p.status, "Open")

		p.project_status = "Completed"
		p.save(ignore_permissions=True)
		self.assertEqual(p.status, "Completed")

	def test_project_status_defaults_to_new(self):
		# PRJ-008: blank project_status becomes New on save.
		p = frappe.get_doc({
			"doctype": "Project",
			"project_name": f"UAT {self._n}",
			"custom_project_id": f"UAT-{self._n}",
			"company": self.company,
		})
		p.insert(ignore_permissions=True)
		self.assertEqual(p.project_status, "New")
		self.assertEqual(p.status, "Open")

	# --- E: company inherit + lock (PRJ-005, PRJ-013) -------------------
	def test_subproject_inherits_company(self):
		parent = self._make_project(company=self.company)
		child = frappe.get_doc({
			"doctype": "Project",
			"project_name": f"UAT sub {self._n}",
			"custom_project_id": f"UAT-SUB-{self._n}",
			"parent_project": parent.name,
			"is_group": 0,
		})
		child.insert(ignore_permissions=True)
		self.assertEqual(child.company, self.company)

	def test_company_locked_after_create(self):
		# PRJ-013: company can't be changed on edit; revert is silent.
		others = frappe.get_all("Company", filters={"name": ("!=", self.company)}, pluck="name")
		p = self._make_project(company=self.company)
		if others:
			p.company = others[0]
			p.save(ignore_permissions=True)
			self.assertEqual(p.company, self.company)

	# --- B: task status sync (TSK-006, TSK-007) -------------------------
	def test_task_status_syncs_to_native(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name, task_status="Yet To Start")
		self.assertEqual(t.status, "Open")

		t.task_status = "In Progress"
		t.save(ignore_permissions=True)
		self.assertEqual(t.status, "Working")

	# --- A + F: TPE updates task + project, no invalid status throw ------
	def test_tpe_updates_task_status_and_no_throw(self):
		# TPE-006: 40% -> In Progress (previously threw on project.status="Working").
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)
		t.reload()
		self.assertEqual(t.progress, 40)
		self.assertEqual(t.task_status, "In Progress")

	def test_tpe_100_completes_task(self):
		# TPE-007
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 100)
		t.reload()
		self.assertEqual(t.progress, 100)
		self.assertEqual(t.task_status, "Completed")

	# --- F: project progress rollup (PRJ-010) ---------------------------
	def test_project_progress_rolls_up(self):
		p = self._make_project(company=self.company)
		t1 = self._make_task(p.name)
		t2 = self._make_task(p.name)
		self._file_tpe(t1.name, 100)
		self._file_tpe(t2.name, 50)
		p.reload()
		self.assertEqual(p.percent_complete, 75)

	def test_parent_progress_weighted_by_subproject_task_count(self):
		# Parent progress blends its direct tasks (weight 1 each) with each
		# subproject's progress weighted by the subproject's task count.
		parent = self._make_project(company=self.company)
		parent.is_group = 1
		parent.save(ignore_permissions=True)

		# Parent direct task at 60%.
		pt = self._make_task(parent.name)
		self._file_tpe(pt.name, 60)

		# Subproject with 3 tasks all at 100% -> sub progress 100, weight 3.
		sub = frappe.get_doc({
			"doctype": "Project",
			"project_name": f"UAT sub {self._n}",
			"custom_project_id": f"UAT-SUB-{self._n}",
			"parent_project": parent.name,
			"is_group": 0,
		}).insert(ignore_permissions=True)
		for _ in range(3):
			st = self._make_task(sub.name)
			self._file_tpe(st.name, 100)

		sub.reload()
		self.assertEqual(sub.percent_complete, 100)

		# (60*1 + 100*3) / (1 + 3) = 90
		parent.reload()
		self.assertEqual(parent.percent_complete, 90)

	# --- G: TPE delete reverts task (TPE-009, TPE-010) ------------------
	def test_delete_latest_tpe_reverts_to_previous(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		self._file_tpe(t.name, 40)
		latest = self._file_tpe(t.name, 100)
		t.reload()
		self.assertEqual(t.progress, 100)

		frappe.delete_doc("Task Progress Entry", latest.name, ignore_permissions=True)
		t.reload()
		self.assertEqual(t.progress, 40)
		self.assertEqual(t.task_status, "In Progress")

	def test_delete_only_tpe_reverts_to_zero(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		only = self._file_tpe(t.name, 60)
		frappe.delete_doc("Task Progress Entry", only.name, ignore_permissions=True)
		t.reload()
		self.assertEqual(t.progress, 0)
		self.assertEqual(t.task_status, "Yet To Start")

	# --- J: blocker requires a note (TPE-011) ---------------------------
	def test_blocker_requires_note(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		with self.assertRaises(frappe.ValidationError):
			self._file_tpe(t.name, 30, blocker=1, blocker_detail=None)

	def test_blocker_with_note_ok(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 30, blocker=1, blocker_detail="Rain stopped the pour")
		self.assertTrue(tpe.name)

	# --- I: guarded cascade delete (PRJ-014, TSK-013) -------------------
	def test_cascade_delete_removes_descendants(self):
		p = self._make_project(company=self.company)
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 20)
		wp = frappe.get_doc({
			"doctype": "Work Package", "project": p.name,
			"work_package_name": "UAT WP", "code": f"WP-{self._n}",
		}).insert(ignore_permissions=True)

		frappe.delete_doc("Project", p.name, ignore_permissions=True)

		self.assertFalse(frappe.db.exists("Project", p.name))
		self.assertFalse(frappe.db.exists("Task", t.name))
		self.assertFalse(frappe.db.exists("Task Progress Entry", tpe.name))
		self.assertFalse(frappe.db.exists("Work Package", wp.name))
