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


# --- Per-persona CRUD matrix -------------------------------------------------
# The permission letters, mapped to the Frappe DocPerm ptypes they represent. "X"
# is cancel+amend (they always move together on a submittable doctype).
_LETTER_PTYPES = {
	"c": ("create",),
	"r": ("read",),
	"w": ("write",),
	"d": ("delete",),
	"s": ("submit",),
	"x": ("cancel", "amend"),
}
# The full ptype universe to check, by submittability: on a submittable doctype we
# assert all of CRWDSX; on a plain master, only CRWD (submit/cancel/amend don't exist).
_SUB_UNIVERSE = "crwdsx"
_NONSUB_UNIVERSE = "crwd"

# Per-persona permission matrices, transcribed from the persona rulings. Each doctype maps
# to the letters the persona SHOULD hold; every OTHER letter in that doctype's universe must
# be DENIED. So both an over-grant (a read-only doctype regaining write) and a lost grant (a
# full doctype losing submit) fail the test. An empty string = NO access (every ptype denied,
# read included) — e.g. the Foreman must not even see Supplier Bill.
#   Submittability caveats: Petty Cash Request and Machinery Usage are plain masters (not
#   submittable), so their "full" is CRWD — a ruling's "S/X" simply don't exist for them.
#   Payment Entry backs the Supplier/Customer "advances" (there is no Advance doctype).
PERSONA_CRUD_MATRIX = {
	"Director / Owner": {
		"Subcontractor Work Order": "crwdsx",
		"Measurement Book": "r",
		"Subcontractor Bill": "r",
		"Purchase Invoice": "crwdsx",  # Supplier Bill
		"Payment Entry": "r",  # Supplier / Customer advances
		"Sales Invoice": "crwdsx",
		"Employee": "r",  # Field Employee
		"Crew": "r",
		"Field Attendance": "r",
		"Machinery": "r",
		"Machinery Usage": "r",
		"Customer": "crwd",
		"Supplier": "crwd",
		"Expense Entry": "crwdsx",
		"Petty Cash Request": "crwd",
	},
	"Foreman / Supervisor": {
		"Purchase Invoice": "",  # Supplier Bill — no access at all (not even read)
		"Employee": "r",  # Field Employee — read-only
		"Crew": "crw",  # maintain membership; no delete
		"Field Attendance": "crwdsx",  # the muster — full
		"Labour Attendance Register": "r",  # derived register — read-only
		"Overtime Attendance Register": "r",  # derived register — read-only
		"Machinery": "r",
		"Machinery Usage": "crw",  # not submittable — CRW is full; the ruling's S is N/A
		"Project": "r",  # must read Project or the project-field selector is empty
	},
}


class TestPersonaCrudMatrix(_PersonaBase):
	"""Per-persona DocPerm matrices, asserted end to end: re-apply the authoritative setup
	(so the test reflects the CURRENT perm maps, not whatever the site drifted to), then check
	each persona user's effective has_permission per ptype per doctype."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Re-converge every matrix to the code — same call the resync patch runs — so the
		# assertions test the maps, independent of the site's migration history. Commit it
		# (it's idempotent site config, not test data) so it survives the per-test rollback
		# and both persona tests see the same applied perms.
		from buildsuite_core.permissions.setup import setup_record_permissions

		setup_record_permissions()
		frappe.db.commit()
		frappe.clear_cache()

	def _allowed(self, email, doctype, ptype):
		return bool(frappe.has_permission(doctype, ptype=ptype, user=email))

	def _assert_persona_matrix(self, persona, matrix):
		email = self._make_user(persona)
		# Sanity: the persona granted exactly its managed role (no stray System Manager that
		# would mask a missing grant behind super-admin access).
		roles = self._roles(email)
		self.assertIn(PERSONA_ROLE[persona], roles)
		self.assertNotIn("System Manager", roles)

		for doctype, expected in matrix.items():
			if not frappe.db.exists("DocType", doctype):
				self.skipTest(f"DocType {doctype!r} not installed on this site")
			submittable = frappe.db.get_value("DocType", doctype, "is_submittable")
			universe = _SUB_UNIVERSE if submittable else _NONSUB_UNIVERSE
			for letter in universe:
				should = letter in expected
				for ptype in _LETTER_PTYPES[letter]:
					with self.subTest(persona=persona, doctype=doctype, ptype=ptype):
						self.assertEqual(
							self._allowed(email, doctype, ptype),
							should,
							f"{persona} {'should' if should else 'should NOT'} have "
							f"{ptype!r} on {doctype!r} (wanted {expected or 'no access'!r})",
						)

	def test_director_matrix(self):
		self._assert_persona_matrix("Director / Owner", PERSONA_CRUD_MATRIX["Director / Owner"])

	def test_foreman_matrix(self):
		self._assert_persona_matrix("Foreman / Supervisor", PERSONA_CRUD_MATRIX["Foreman / Supervisor"])
