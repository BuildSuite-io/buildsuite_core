# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Permission-matrix tests — persona role sync (what happens when a user's persona
changes) and per-persona report access, encoded from the Dashboard/Report access
sheets.

Two dimensions are covered here:

* **Persona role sync** (``TestPersonaRoleSync``) — creating a user with a persona,
  and *switching* a user's persona, must leave exactly the right BuildSuite roles.
  This is where the reported "System Manager carried over after switching persona"
  bug lives.

* **Report access** (``TestReportAccessMatrix``) — the six role-gated Script Reports
  must be runnable by exactly the personas the access sheet says, and no others.

Dashboard / workspace visibility is intentionally NOT tested here: it is enforced
entirely client-side (``frontend/src/data/roles.js`` ``WORKSPACE_VISIBILITY``), so
there is nothing on the Python backend to assert. See the module docstring note.
"""

import frappe

from buildsuite_core.permissions.setup import WORKFLOW_EDITOR_ROLE
from buildsuite_core.tests.base import BuildSuiteTestCase

# persona record name -> the single BuildSuite/native role it manages.
PERSONA_ROLE = {
	"Director / Owner": "BuildSuite Director",
	"Project Manager": "BuildSuite PM",
	"Estimator": "BuildSuite Estimator",
	"Quantity Surveyor": "BuildSuite QS",
	"Site Engineer": "BuildSuite Site Engineer",
	"Foreman / Supervisor": "BuildSuite Foreman",
	"Procurement Officer": "BuildSuite Procurement Officer",
	"Store Keeper": "BuildSuite Store Keeper",
	"Accountant": "BuildSuite Accountant",
	"HR Manager": "BuildSuite HR Manager",
	"System Manager (Admin)": "System Manager",
	"BuildSuite Administrator": "BuildSuite Administrator",
}
ADMIN_PERSONAS = ("System Manager (Admin)", "BuildSuite Administrator")
FIELD_PERSONAS = [p for p in PERSONA_ROLE if p not in ADMIN_PERSONAS]
MANAGED_ROLES = set(PERSONA_ROLE.values())


class _PersonaBase(BuildSuiteTestCase):
	def _make_user(self, persona):
		email = f"pm-{persona[:4].strip().lower().replace(' ', '')}-{self._n}-{frappe.generate_hash(length=4)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Matrix",
				"user_type": "System User",
				"send_welcome_email": 0,
				"persona": persona,
			}
		).insert(ignore_permissions=True)
		return email

	def _switch(self, email, persona):
		u = frappe.get_doc("User", email)
		u.persona = persona
		u.save(ignore_permissions=True)

	def _roles(self, email):
		return {r.role for r in frappe.get_doc("User", email).roles}


class TestPersonaRoleSync(_PersonaBase):
	# --- granting -------------------------------------------------------------
	def test_each_persona_grants_only_its_managed_role(self):
		"""Setting a persona grants that persona's role + the workflow-editor marker,
		and none of the OTHER personas' managed roles."""
		for persona, role in PERSONA_ROLE.items():
			with self.subTest(persona=persona):
				email = self._make_user(persona)
				roles = self._roles(email)
				self.assertIn(role, roles, f"{persona} should grant {role}")
				self.assertIn(WORKFLOW_EDITOR_ROLE, roles, f"{persona} should grant the workflow-editor role")
				stray = (MANAGED_ROLES - {role}) & roles
				self.assertFalse(stray, f"{persona} leaked other personas' roles: {stray}")

	# --- switching between field personas ------------------------------------
	def test_switch_chain_keeps_only_current_field_persona_role(self):
		"""Switch one user through every ordinary persona in turn. At each step it must
		hold the new persona's role and NONE of the personas seen earlier — the running
		'changes of persona' the report sheet cares about. (One user, to stay under the
		User-creation throttle.)"""
		chain = FIELD_PERSONAS
		email = self._make_user(chain[0])
		seen = {chain[0]}
		for nxt in chain[1:]:
			self._switch(email, nxt)
			seen.add(nxt)
			roles = self._roles(email)
			with self.subTest(step=nxt):
				self.assertIn(PERSONA_ROLE[nxt], roles, f"{nxt} role not granted after switch")
				stale = {PERSONA_ROLE[p] for p in seen if p != nxt} & roles
				self.assertFalse(stale, f"stale role(s) survived after switching to {nxt}: {stale}")

	# --- switching AWAY FROM an admin persona (the reported bug) --------------
	def test_switch_away_from_admin_persona_strips_admin_role(self):
		"""THE REPORTED BUG. A user on an admin persona, moved to an ordinary persona,
		must lose the admin role that only the admin persona granted."""
		for admin in ADMIN_PERSONAS:
			with self.subTest(frm=admin):
				email = self._make_user(admin)
				self.assertIn(PERSONA_ROLE[admin], self._roles(email))
				self._switch(email, "Site Engineer")
				roles = self._roles(email)
				self.assertNotIn(
					PERSONA_ROLE[admin],
					roles,
					f"{PERSONA_ROLE[admin]} (granted only by the {admin} persona) survived the switch to Site Engineer",
				)
				self.assertIn("BuildSuite Site Engineer", roles)

	# --- switching INTO an admin persona -------------------------------------
	def test_switch_into_admin_persona_grants_admin_role(self):
		for admin in ADMIN_PERSONAS:
			with self.subTest(to=admin):
				email = self._make_user("Site Engineer")
				self._switch(email, admin)
				roles = self._roles(email)
				self.assertIn(PERSONA_ROLE[admin], roles)
				self.assertNotIn("BuildSuite Site Engineer", roles, "stale Site Engineer role survived")

	# --- round trip through the admin persona --------------------------------
	def test_round_trip_through_admin_persona(self):
		"""Admin -> field -> admin: the admin role is gone in the middle and back at
		the end (no stale accumulation, correct re-grant)."""
		email = self._make_user("System Manager (Admin)")
		self._switch(email, "Site Engineer")
		self.assertNotIn("System Manager", self._roles(email), "System Manager not dropped mid round-trip")
		self._switch(email, "System Manager (Admin)")
		self.assertIn("System Manager", self._roles(email), "System Manager not re-granted on return")

	# --- manual (non-persona) roles are preserved ----------------------------
	def test_manual_role_survives_persona_switch(self):
		"""A role added on top of a persona (not granted by it) must never be stripped
		by a later persona switch — combined-responsibility users are legitimate."""
		email = self._make_user("Project Manager")
		u = frappe.get_doc("User", email)
		u.append("roles", {"role": "BuildSuite QS"})  # manual add, not from the PM persona
		u.save(ignore_permissions=True)
		self._switch(email, "Estimator")
		roles = self._roles(email)
		self.assertIn("BuildSuite QS", roles, "manually-added role was wrongly stripped on switch")
		self.assertIn("BuildSuite Estimator", roles)
		self.assertNotIn("BuildSuite PM", roles, "stale PM role survived")

	# --- no accumulation across repeated switches ----------------------------
	def test_repeated_switches_do_not_accumulate_roles(self):
		email = self._make_user("Project Manager")
		self._switch(email, "Estimator")
		self._switch(email, "Quantity Surveyor")
		managed = self._roles(email) & MANAGED_ROLES
		self.assertEqual(
			managed,
			{"BuildSuite QS"},
			f"only the final persona's role should remain, found {managed}",
		)


# The six role-gated Script Reports, transcribed from the "Report access by persona"
# sheet: the personas each report should be runnable by. "O" (by-decision) cells are
# treated as expected-access. The other matrix rows are ungated route tiles / bespoke
# Vue views (no Report to gate) and can't be asserted here.
REPORT_MATRIX = {
	"Billing and Collection": {
		"Director / Owner",
		"Project Manager",
		"Accountant",
		"System Manager (Admin)",
		"BuildSuite Administrator",
	},
	"Subcontractor Position": {
		"Director / Owner",
		"Project Manager",
		"Quantity Surveyor",
		"Procurement Officer",  # "O" — by decision (T3 exception)
		"Accountant",
		"System Manager (Admin)",
		"BuildSuite Administrator",
	},
	"Material Status": {
		"Director / Owner",
		"Project Manager",
		"Quantity Surveyor",
		"Site Engineer",
		"Foreman / Supervisor",
		"Procurement Officer",
		"Store Keeper",
		"System Manager (Admin)",
		"BuildSuite Administrator",
	},
	"Subcontractor Work Order Register": {
		"Director / Owner",
		"Project Manager",
		"Quantity Surveyor",
		"Accountant",
		"System Manager (Admin)",
		"BuildSuite Administrator",
	},
	"Measurement Book Register": {
		"Director / Owner",
		"Project Manager",
		"Quantity Surveyor",
		"Site Engineer",
		"Accountant",
		"System Manager (Admin)",
		"BuildSuite Administrator",
	},
	"Subcontractor Bill Register": {
		"Director / Owner",
		"Project Manager",
		"Quantity Surveyor",
		"Accountant",
		"System Manager (Admin)",
		"BuildSuite Administrator",
	},
}


class TestReportAccessMatrix(_PersonaBase):
	def _can_run(self, email, report):
		"""True if the given user is allowed to run the report (its is_permitted gate)."""
		frappe.set_user(email)
		try:
			return bool(frappe.get_cached_doc("Report", report).is_permitted())
		finally:
			frappe.set_user("Administrator")

	def test_report_access_matches_the_matrix(self):
		"""Each of the six role-gated reports must be runnable by exactly the personas
		the access sheet lists — a persona outside the row must be denied."""
		# One user per persona, reused across reports.
		users = {p: self._make_user(p) for p in PERSONA_ROLE}
		for report, allowed_personas in REPORT_MATRIX.items():
			if not frappe.db.exists("Report", report):
				self.skipTest(f"Report {report!r} not installed on this site")
			for persona, email in users.items():
				expected = persona in allowed_personas
				with self.subTest(report=report, persona=persona):
					self.assertEqual(
						self._can_run(email, report),
						expected,
						f"{persona} {'should' if expected else 'should NOT'} be able to run {report!r}",
					)
