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
		# PRM-016 — HR Manager reads labour (TPE) across projects while not teamed. HR Manager is
		# a FLIP role: unrestricted until added to a Project Team, scoped to teamed projects after.
		hr = self._make_persona_user("HR Manager", "hr")
		p = self._make_project(company=self.company)  # HR not on the team → sees everything
		t = self._make_task(p.name)
		tpe = self._file_tpe(t.name, 30)

		frappe.set_user(hr)
		try:
			doc = frappe.get_doc("Task Progress Entry", tpe.name)
			self.assertTrue(doc.has_permission("read"))
		finally:
			frappe.set_user("Administrator")

	def test_project_visibility_model(self):
		# PRM-017 — the team-scoped visibility model (permissions/project.py):
		#   FLIP roles (e.g. Estimator/QS/Procurement/Store Keeper/Accountant/HR/PM): see every
		#     project until added to any team, then scoped to their teamed projects.
		#   TEAM_ONLY roles (Site Engineer, Foreman): always scoped — nothing until teamed.
		#   EXEMPT roles (Director, System Manager, BuildSuite Administrator): never scoped.
		from buildsuite_core.permissions.project import get_project_permission_query as query

		def team_project(user, tag):
			return frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"VIS {tag} {self._n}",
					"custom_project_id": f"VIS-{tag}-{self._n}",
					"project_status": "Ongoing",
					"company": self.company,
					"custom_team_members": [{"user": user}],
				}
			).insert(ignore_permissions=True)

		# FLIP: unteamed → unrestricted; teamed → scoped to own projects.
		est = self._make_persona_user("Estimator", "estvis")
		self.assertEqual(query(est), "", "an unteamed FLIP role must not be scoped")
		team_project(est, "est")
		scoped = query(est)
		self.assertIn("Project Team", scoped)
		self.assertIn(frappe.db.escape(est), scoped)

		# TEAM_ONLY: scoped even with no team membership.
		fm = self._make_persona_user("Foreman / Supervisor", "fmvis")
		self.assertIn("Project Team", query(fm))

		# EXEMPT: never scoped, even when on a team.
		d = self._make_persona_user("Director / Owner", "dirvis")
		team_project(d, "dir")
		self.assertEqual(query(d), "", "an EXEMPT role must never be scoped")

	# --- Persona.project_visibility: team scoping set per persona, not per role ----------------
	def _persona(self, roles, visibility):
		return frappe.get_doc(
			{
				"doctype": "Persona",
				"persona_name": f"Scoping {visibility[:8]} {frappe.generate_hash(length=5)}",
				"enabled": 1,
				"project_visibility": visibility,
				"roles": [{"role": r} for r in roles],
			}
		).insert(ignore_permissions=True)

	def test_default_personas_keep_the_scoping_they_had(self):
		from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import DEFAULT_PROJECT_VISIBILITY

		for persona, visibility in DEFAULT_PROJECT_VISIBILITY.items():
			self.assertEqual(
				frappe.db.get_value("Persona", persona, "project_visibility"), visibility, persona
			)

	def test_a_persona_on_a_site_role_can_be_set_to_see_every_project(self):
		# Site Engineer's role was always team-scoped in code; a persona can now open it up.
		from buildsuite_core.permissions.project import get_project_permission_query as query

		persona = self._persona(["BuildSuite Site Engineer"], "All projects")
		user = self._make_persona_user(persona.name, "seall")
		self.assertEqual(query(user), "")

		# Doc-level too: a task on a project they are not teamed on is readable.
		other = self._make_project(company=self.company)
		task = self._make_task(other.name)
		frappe.set_user(user)
		try:
			self.assertTrue(frappe.get_doc("Task", task.name).has_permission("read"))
		finally:
			frappe.set_user("Administrator")

	def test_a_persona_on_an_exempt_role_can_be_narrowed_to_its_teams(self):
		from buildsuite_core.permissions.project import get_project_permission_query as query

		persona = self._persona(["BuildSuite Director"], "Team projects only")
		user = self._make_persona_user(persona.name, "dirteam")
		self.assertIn("Project Team", query(user))

	def test_a_custom_role_persona_follows_its_setting(self):
		# A persona built from a role BuildSuite does not ship — "All projects" leaves access to
		# its DocPerms (Frappe's default processing); "until teamed" narrows once teamed.
		from buildsuite_core.permissions.project import get_project_permission_query as query

		everything = self._make_persona_user(self._persona(["Projects User"], "All projects").name, "cuall")
		self.assertEqual(query(everything), "")

		flip = self._make_persona_user(
			self._persona(["Projects User"], "All projects until added to a team").name, "cuflip"
		)
		self.assertEqual(query(flip), "")
		self._project_with_member(flip)
		self.assertIn("Project Team", query(flip))

	def test_changing_the_setting_takes_effect_for_existing_users(self):
		from buildsuite_core.permissions.project import get_project_permission_query as query

		persona = self._persona(["BuildSuite Site Engineer"], "Team projects only")
		user = self._make_persona_user(persona.name, "sechg")
		self.assertIn("Project Team", query(user))
		persona.project_visibility = "All projects"
		persona.save(ignore_permissions=True)
		self.assertEqual(query(user), "")

	def test_system_manager_is_never_scoped_whatever_the_persona(self):
		from buildsuite_core.permissions.project import get_project_permission_query as query

		persona = self._persona(["BuildSuite Site Engineer"], "Team projects only")
		user = self._make_persona_user(persona.name, "smteam")
		frappe.get_doc("User", user).add_roles("System Manager")
		self.assertEqual(query(user), "")

	def test_a_user_without_a_persona_falls_back_to_the_role_rule(self):
		from buildsuite_core.permissions.project import get_project_permission_query as query

		email = f"nopersona-{self._n}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "NP", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		frappe.get_doc("User", email).add_roles("BuildSuite PM")  # PM: all until teamed
		self.assertEqual(query(email), "")
		self._project_with_member(email)
		self.assertIn("Project Team", query(email))

	def test_the_patch_derives_a_custom_personas_setting_from_its_roles(self):
		from buildsuite_core.patches.set_persona_project_visibility import execute

		custom_pm = self._persona(["BuildSuite PM"], "Team projects only")
		custom_other = self._persona(["Projects User"], "All projects")
		frappe.db.set_value("Persona", "Director / Owner", "project_visibility", "Team projects only")
		execute()
		self.assertEqual(
			frappe.db.get_value("Persona", custom_pm.name, "project_visibility"),
			"All projects until added to a team",
		)
		self.assertEqual(
			frappe.db.get_value("Persona", custom_other.name, "project_visibility"), "Team projects only"
		)
		self.assertEqual(
			frappe.db.get_value("Persona", "Director / Owner", "project_visibility"), "All projects"
		)

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

	def test_admin_can_submit_subcontractor_work_order(self):
		# M3 — the Work Order is submittable; the admin tier (and the subcontract full
		# roles) must have submit/cancel/amend, not just CRWD.
		self._as("BuildSuite Administrator", "basub")
		try:
			for ptype in ("create", "write", "delete", "submit", "cancel", "amend"):
				self.assertTrue(frappe.has_permission("Subcontractor Work Order", ptype), ptype)
		finally:
			frappe.set_user("Administrator")

	def test_admin_full_on_m3_masters(self):
		# M3 — the admin tier gets full CRWD on the worker/crew/equipment/commercial
		# masters that the matrix had left read-only (Employee, Customer) or ungranted
		# (Crew, Machinery Type).
		self._as("BuildSuite Administrator", "bamaster")
		try:
			for dt in ("Employee", "Crew", "Machinery Type", "Customer"):
				self.assertTrue(frappe.has_permission(dt, "create"), dt)
				self.assertTrue(frappe.has_permission(dt, "write"), dt)
				self.assertTrue(frappe.has_permission(dt, "delete"), dt)
		finally:
			frappe.set_user("Administrator")

	def test_master_upgrade_preserves_picker_read(self):
		# The Employee/Customer write upgrade must not revoke the link-picker read that
		# other roles rely on — QS still reads both even though it cannot write them.
		self._as("Quantity Surveyor", "qspick")
		try:
			for dt in ("Employee", "Customer"):
				self.assertTrue(frappe.has_permission(dt, "read"), dt)
				self.assertFalse(frappe.has_permission(dt, "delete"), dt)
		finally:
			frappe.set_user("Administrator")

	def test_system_manager_retains_full_access(self):
		# A doctype's Custom DocPerms COMPLETELY override its standard perms, so adding any
		# BuildSuite grant would strip System Manager (the native super-admin) unless it is
		# re-granted. It must stay full — create + delete (+ submit on submittable doctypes) —
		# on every doctype the matrices touch.
		email = f"smtest-{self._n}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "SM",
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": "System Manager"}],
			}
		).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			for dt in (
				"Customer",
				"Supplier",
				"Sales Invoice",
				"Payment Entry",
				"Subcontractor Work Order",
				"Subcontractor Bill",
				"Expense Entry",
				"Employee",
				"Crew",
			):
				self.assertTrue(frappe.has_permission(dt, "create"), dt)
				self.assertTrue(frappe.has_permission(dt, "delete"), dt)
			for dt in ("Sales Invoice", "Subcontractor Work Order", "Subcontractor Bill"):
				self.assertTrue(frappe.has_permission(dt, "submit"), dt)
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

	# --- M3 access control (Workforce / Equipment / Project Finance) ----------
	def test_store_keeper_maintains_machinery(self):
		# M3-EQP — Store Keeper (with Procurement) maintains the Machinery register: full
		# CRUD on Machinery + Machinery Usage; the muster (Field Attendance) is hidden.
		self._as("Store Keeper", "storeeq")
		try:
			for dt in ("Machinery", "Machinery Usage"):
				self.assertTrue(frappe.has_permission(dt, "create"), dt)
				self.assertTrue(frappe.has_permission(dt, "write"), dt)
			self.assertFalse(frappe.has_permission("Field Attendance", "read"))
		finally:
			frappe.set_user("Administrator")

	def test_site_engineer_equipment_split(self):
		# M3-EQP — Site Engineer records plant usage (create Machinery Usage) but only
		# reads the Machinery register (Procurement/Store own it).
		self._as("Site Engineer", "seeq")
		try:
			self.assertTrue(frappe.has_permission("Machinery Usage", "create"))
			self.assertTrue(frappe.has_permission("Machinery", "read"))
			self.assertFalse(frappe.has_permission("Machinery", "write"))
		finally:
			frappe.set_user("Administrator")

	def test_derived_attendance_read_only(self):
		# M3-WF — the derived Labour/Overtime registers are read-only for every role;
		# they are system-written when the Field Attendance muster is submitted.
		self._as("Foreman / Supervisor", "fmwf")
		try:
			for dt in ("Labour Attendance Register", "Overtime Attendance Register"):
				self.assertTrue(frappe.has_permission(dt, "read"), dt)
				self.assertFalse(frappe.has_permission(dt, "write"), dt)
				self.assertFalse(frappe.has_permission(dt, "create"), dt)
		finally:
			frappe.set_user("Administrator")

	def test_hr_manager_creates_and_deletes_attendance_registers(self):
		# HR keeps the attendance books: it may add a register by hand and delete one, but editing
		# (and submit / cancel) stays with the muster.
		self._as("HR Manager", "hrar")
		try:
			for dt in ("Labour Attendance Register", "Overtime Attendance Register"):
				for ptype in ("read", "create", "delete"):
					self.assertTrue(frappe.has_permission(dt, ptype), f"{dt} {ptype}")
				for ptype in ("write", "submit", "cancel"):
					self.assertFalse(frappe.has_permission(dt, ptype), f"{dt} {ptype}")
		finally:
			frappe.set_user("Administrator")

	def test_hr_register_patch_adds_only_create_and_delete(self):
		# Live sites: the patch raises create + delete on HR Manager's own rule and leaves the
		# rest of that rule (here a site-edited `export` = 0) and every other role alone.
		from buildsuite_core.patches import grant_hr_manager_attendance_registers as patch

		dt, role = "Labour Attendance Register", "BuildSuite HR Manager"
		perm = {"parent": dt, "role": role, "permlevel": 0}
		frappe.db.set_value("Custom DocPerm", perm, {"create": 0, "delete": 0, "export": 0})
		foreman = frappe.db.get_value(
			"Custom DocPerm",
			{"parent": dt, "role": "BuildSuite Foreman", "permlevel": 0},
			["read", "create", "delete", "write"],
			as_dict=True,
		)
		patch.execute()
		row = frappe.db.get_value(
			"Custom DocPerm", perm, ["read", "create", "delete", "export", "write"], as_dict=True
		)
		self.assertEqual((row.read, row.create, row.delete, row.export, row.write), (1, 1, 1, 0, 0))
		self.assertEqual(
			frappe.db.get_value(
				"Custom DocPerm",
				{"parent": dt, "role": "BuildSuite Foreman", "permlevel": 0},
				["read", "create", "delete", "write"],
				as_dict=True,
			),
			foreman,
		)

	def test_field_attendance_site_submits(self):
		# M3-WF — Site Engineer submits the muster; Estimator has no access to it.
		self._as("Site Engineer", "sewf")
		try:
			self.assertTrue(frappe.has_permission("Field Attendance", "create"))
			self.assertTrue(frappe.has_permission("Field Attendance", "submit"))
		finally:
			frappe.set_user("Administrator")
		self._as("Estimator", "estwf")
		try:
			self.assertFalse(frappe.has_permission("Field Attendance", "read"))
		finally:
			frappe.set_user("Administrator")

	def test_accountant_finance_vs_pm_read(self):
		# M3-PF — Accountant raises + submits Sales Invoice and Payment Entry; PM only
		# reads the invoice (billing context) and cannot create it.
		self._as("Accountant", "acctpf")
		try:
			for dt in ("Sales Invoice", "Payment Entry"):
				self.assertTrue(frappe.has_permission(dt, "create"), dt)
				self.assertTrue(frappe.has_permission(dt, "submit"), dt)
		finally:
			frappe.set_user("Administrator")
		self._as("Project Manager", "pmpf")
		try:
			self.assertTrue(frappe.has_permission("Sales Invoice", "read"))
			self.assertFalse(frappe.has_permission("Sales Invoice", "create"))
		finally:
			frappe.set_user("Administrator")
