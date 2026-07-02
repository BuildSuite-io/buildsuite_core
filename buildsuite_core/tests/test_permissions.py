# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Record-level permission tests (run as a specific persona via frappe.set_user).

These depend on the role DocPerms + record-level hooks seeded by
permissions/setup.py (present after migrate)."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPermissions(BuildSuiteTestCase):
	def _make_persona_user(self, persona, prefix):
		email = f"{prefix}-{self._n}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": prefix.upper(),
				"send_welcome_email": 0,
				"user_type": "System User",
				"persona": persona,
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		return email

	def _project_with_member(self, user):
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"PERM {self._n}",
				"custom_project_id": f"PERM-{self._n}",
				"project_status": "Ongoing",
				"company": self.company,
				"custom_team_members": [{"user": user}],
			}
		).insert(ignore_permissions=True)

	def test_site_engineer_edits_own_task_only(self):
		# PRM-008 — a Site Engineer can edit/delete tasks they created, not others'.
		se = self._make_persona_user("Site Engineer", "se")
		p = self._project_with_member(se)
		# A task created by Administrator (owner != SE).
		other = self._make_task(p.name)

		frappe.set_user(se)
		try:
			own = frappe.get_doc(
				{
					"doctype": "Task",
					"subject": f"own {self._n}",
					"project": p.name,
					"task_status": "Yet To Start",
				}
			).insert()
			own.subject = "own edited"
			own.save()  # must not raise — SE owns it

			other_doc = frappe.get_doc("Task", other.name)
			other_doc.subject = "nope"
			self.assertRaises(frappe.PermissionError, other_doc.save)
		finally:
			frappe.set_user("Administrator")

	def test_foreman_cannot_create_project(self):
		# PRM-013 — Foreman has no Project create permission.
		fm = self._make_persona_user("Foreman / Supervisor", "fm")
		frappe.set_user(fm)
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"FM {self._n}",
					"custom_project_id": f"FM-{self._n}",
					"company": self.company,
				}
			)
			self.assertRaises(frappe.PermissionError, doc.insert)
		finally:
			frappe.set_user("Administrator")

	def test_director_full_crud(self):
		# PRM-001 — Director can create Project, Task and Stage Planning.
		d = self._make_persona_user("Director / Owner", "dir")
		frappe.set_user(d)
		try:
			p = frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"DIR {self._n}",
					"custom_project_id": f"DIR-{self._n}",
					"company": self.company,
				}
			).insert()
			t = frappe.get_doc(
				{
					"doctype": "Task",
					"subject": f"DIR {self._n}",
					"project": p.name,
					"task_status": "Yet To Start",
				}
			).insert()
			st = frappe.get_doc(
				{
					"doctype": "Stage Planning",
					"stage_name": f"DIR {self._n}",
					"project": p.name,
				}
			).insert()
			self.assertTrue(p.name and t.name and st.name)
		finally:
			frappe.set_user("Administrator")

	def test_pm_can_approve_stage(self):
		# PRM-003 / SAW-009 — a PM can approve a Pending stage.
		from frappe.model.workflow import apply_workflow

		pm = self._make_persona_user("Project Manager", "pmapp")
		p = self._make_project(company=self.company)
		st = frappe.get_doc(
			{
				"doctype": "Stage Planning",
				"stage_name": f"APP {self._n}",
				"project": p.name,
				"workflow_state": "Draft",
			}
		).insert(ignore_permissions=True)
		apply_workflow(st, "Submit for Approval")  # as Administrator → Pending

		frappe.set_user(pm)
		try:
			st2 = frappe.get_doc("Stage Planning", st.name)
			apply_workflow(st2, "Approve")
			st2.reload()
			self.assertEqual(st2.workflow_state, "Approved")
		finally:
			frappe.set_user("Administrator")

	def test_site_engineer_can_file_tpe(self):
		# PRM-009 — a Site Engineer can file a progress entry (unconditional create).
		from frappe.utils import today

		se = self._make_persona_user("Site Engineer", "setpe")
		p = self._project_with_member(se)
		t = self._make_task(p.name)
		frappe.set_user(se)
		try:
			tpe = frappe.get_doc(
				{
					"doctype": "Task Progress Entry",
					"task": t.name,
					"entry_date": today(),
					"cumulative_progress": 30,
				}
			).insert()
			self.assertTrue(tpe.name)
		finally:
			frappe.set_user("Administrator")

	def test_approved_stage_delete_is_approver_only(self):
		# SAW-012 — an own-scope creator cannot delete their Approved stage; an
		# approver (full role) can.
		from frappe.model.workflow import apply_workflow

		se = self._make_persona_user("Site Engineer", "sedel")
		p = self._project_with_member(se)
		frappe.set_user(se)
		try:
			st = frappe.get_doc(
				{
					"doctype": "Stage Planning",
					"stage_name": f"DEL {self._n}",
					"project": p.name,
					"workflow_state": "Draft",
				}
			).insert()
			apply_workflow(st, "Submit for Approval")
		finally:
			frappe.set_user("Administrator")

		st = frappe.get_doc("Stage Planning", st.name)
		apply_workflow(st, "Approve")  # Administrator approves
		st.reload()
		self.assertEqual(st.workflow_state, "Approved")

		frappe.set_user(se)
		try:
			self.assertRaises(
				frappe.PermissionError,
				lambda: frappe.delete_doc("Stage Planning", st.name),
			)
		finally:
			frappe.set_user("Administrator")

		frappe.delete_doc("Stage Planning", st.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Stage Planning", st.name))

	def test_hr_manager_reads_tpe_across_projects(self):
		# PRM-016 — HR Manager reads labour (TPE) across projects, exempt from team scope.
		hr = self._make_persona_user("HR Manager", "hr")
		p = self._make_project(company=self.company)  # HR not on the team
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 30)

		frappe.set_user(hr)
		try:
			doc = frappe.get_doc("Task Progress Entry", tpe.name)
			self.assertTrue(doc.has_permission("read"))
		finally:
			frappe.set_user("Administrator")

	# --- M2 access control (Estimation / Rate Master / Purchase & Stock) -----
	def _as(self, persona, prefix):
		user = self._make_persona_user(persona, prefix)
		frappe.set_user(user)
		return user

	def test_estimator_full_estimation_crud(self):
		# PERM-001 — Estimator has full CRUD across the estimation DocTypes.
		self._as("Estimator", "est")
		try:
			for dt in ("BOQ", "Assembly", "Estimate Template", "Construction Rate Master"):
				self.assertTrue(frappe.has_permission(dt, "create"), dt)
				self.assertTrue(frappe.has_permission(dt, "write"), dt)
				self.assertTrue(frappe.has_permission(dt, "delete"), dt)
		finally:
			frappe.set_user("Administrator")

	def test_procurement_rate_master_read_only(self):
		# PERM-004 / PERM-006 — Procurement Officer reads Rate Master but cannot write
		# it from the form; PERM-003 — Estimation (BOQ) is hidden.
		self._as("Procurement Officer", "proc")
		try:
			self.assertTrue(frappe.has_permission("Construction Rate Master", "read"))
			self.assertFalse(frappe.has_permission("Construction Rate Master", "write"))
			self.assertFalse(frappe.has_permission("BOQ", "read"))
		finally:
			frappe.set_user("Administrator")

	def test_procurement_full_buying(self):
		# PERM-007 — Procurement Officer: create + submit on the buying transactions.
		self._as("Procurement Officer", "proc")
		try:
			for dt in ("Material Request", "Purchase Order", "Purchase Receipt"):
				self.assertTrue(frappe.has_permission(dt, "create"), dt)
				self.assertTrue(frappe.has_permission(dt, "submit"), dt)
		finally:
			frappe.set_user("Administrator")

	def test_site_engineer_mr_raise_only(self):
		# PERM-008 — Site Engineer can create a Material Request but not delete it,
		# and has no estimation access.
		self._as("Site Engineer", "se")
		try:
			self.assertTrue(frappe.has_permission("Material Request", "create"))
			self.assertFalse(frappe.has_permission("Material Request", "delete"))
			self.assertFalse(frappe.has_permission("Assembly", "read"))
		finally:
			frappe.set_user("Administrator")

	def test_hr_no_procurement_or_estimation(self):
		# PERM-015 — HR Manager sees neither procurement nor estimation DocTypes.
		self._as("HR Manager", "hrm")
		try:
			self.assertFalse(frappe.has_permission("Construction Rate Master", "read"))
			self.assertFalse(frappe.has_permission("Material Request", "read"))
		finally:
			frappe.set_user("Administrator")

	def test_rate_update_guard_rejects_non_governance(self):
		# PERM-013 — the PO-submit rate-update endpoint rejects a non-governance role
		# and accepts the empowered Procurement Officer.
		from buildsuite_core.api import rate_master as rm

		self._as("Foreman / Supervisor", "fm")
		try:
			self.assertRaises(
				frappe.PermissionError,
				rm.update_rates_from_po,
				purchase_order="PO-TEST",
				updates=[],
			)
		finally:
			frappe.set_user("Administrator")

		self._as("Procurement Officer", "proc")
		try:
			self.assertEqual(rm.update_rates_from_po(purchase_order="PO-TEST", updates=[]), [])
		finally:
			frappe.set_user("Administrator")
