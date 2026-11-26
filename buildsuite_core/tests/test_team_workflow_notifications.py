# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Team-scoped workflow notifications: a workflow ticked "Team-scoped notifications" notifies the next
step's users on states marked "Send Email"; a user whose persona follows the project team, and who is
on a team, only for their own team's projects; everyone else as usual; nobody left → all holders."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.team_workflow_notifications import recipients, workflow_validate

SCO = "Scope Change Order"
PM_ROLE = "BuildSuite PM"


class TestTeamScopedWorkflowNotifications(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.workflow = frappe.db.get_value("Workflow", {"document_type": SCO, "is_active": 1})
		if not self.workflow:
			self.skipTest("no active Scope Change Order workflow on this site")
		if not frappe.db.get_value("Persona", "Project Manager", "team_scoped_notifications"):
			frappe.db.set_value("Persona", "Project Manager", "team_scoped_notifications", 1)
		self._configure(ticked=1, send_email=1)

		self.project = self._project()
		other = self._project()
		self.on_team = self._user("on-team", persona="Project Manager", team=self.project)
		self.elsewhere = self._user("elsewhere", persona="Project Manager", team=other)
		self.no_team = self._user("no-team", persona="Project Manager")
		self.no_persona = self._user("no-persona", role=PM_ROLE)
		# a persona that oversees every project overrides the workflow's team scoping
		frappe.db.set_value("Persona", "Director / Owner", "team_scoped_notifications", 0)
		frappe.clear_document_cache("Persona", "Director / Owner")
		self.not_scoped = self._user("not-scoped", persona="Director / Owner", role=PM_ROLE)

	def _configure(self, ticked, send_email):
		frappe.db.set_value("Workflow", self.workflow, "custom_team_scoped_notifications", ticked)
		frappe.db.set_value(
			"Workflow Document State",
			{"parent": self.workflow, "state": "Pending Approval"},
			"send_email",
			send_email,
		)
		frappe.clear_document_cache("Workflow", self.workflow)
		self.addCleanup(frappe.clear_document_cache, "Workflow", self.workflow)

	def _project(self):
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"TWN {frappe.generate_hash(length=6)}",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

	def _user(self, tag, persona=None, role=None, team=None):
		email = f"twn-{tag}-{self._n}-{frappe.generate_hash(length=5)}@example.com"
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": tag,
				"send_welcome_email": 0,
				**({"persona": persona} if persona else {}),
			}
		).insert(ignore_permissions=True)
		if role:
			user.add_roles(role)
		if team:
			team.append("custom_team_members", {"user": email})
			team.save(ignore_permissions=True)
		return email

	def _raise_sco(self):
		return frappe.get_doc(
			{
				"doctype": SCO,
				"project": self.project.name,
				"title": "Extra lighting",
				"reason": "Client request",
			}
		).insert(ignore_permissions=True)

	def _notified(self, user, sco):
		return bool(
			frappe.db.exists(
				"Notification Log", {"for_user": user, "document_type": SCO, "document_name": sco.name}
			)
		)

	def test_team_scoped_personas_follow_the_project_team(self):
		sco = self._raise_sco()
		self.assertTrue(self._notified(self.on_team, sco))  # on this project's team
		self.assertFalse(self._notified(self.elsewhere, sco))  # scoped, on another project's team
		self.assertFalse(self._notified(self.no_team, sco))  # scoped, on no team: still not this one
		self.assertFalse(self._notified(self.no_persona, sco))  # no persona: scoped by default
		self.assertTrue(self._notified(self.not_scoped, sco))  # persona not team-scoped overrides

	def test_a_project_without_a_team_notifies_all_holders(self):
		role = f"TWN Role {frappe.generate_hash(length=5)}"
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
			ignore_permissions=True
		)
		for user in (self.on_team, self.no_team, self.no_persona):
			frappe.get_doc("User", user).add_roles(role)
		self.project.set("custom_team_members", [])
		self.project.save(ignore_permissions=True)
		sco = self._raise_sco()
		self.assertEqual(recipients(sco, {role}), {self.on_team, self.no_team, self.no_persona})

	def test_everyone_with_the_role_when_nobody_would_be_told(self):
		"""If every holder of the role is scoped away, all of them are told: never nobody."""
		role = f"TWN Role {frappe.generate_hash(length=5)}"
		frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
			ignore_permissions=True
		)
		frappe.get_doc("User", self.elsewhere).add_roles(role)  # its only holder, scoped away
		sco = self._raise_sco()
		self.assertEqual(recipients(sco, {role}), {self.elsewhere})

	def test_a_workflow_not_ticked_notifies_nobody(self):
		self._configure(ticked=0, send_email=1)
		sco = self._raise_sco()
		self.assertFalse(self._notified(self.on_team, sco))
		self.assertFalse(self._notified(self.not_scoped, sco))

	def test_a_state_without_send_email_notifies_nobody(self):
		self._configure(ticked=1, send_email=0)
		sco = self._raise_sco()
		self.assertFalse(self._notified(self.on_team, sco))

	def test_ticking_switches_off_the_workflows_own_email(self):
		wf = frappe.get_doc("Workflow", self.workflow)
		wf.custom_team_scoped_notifications = 1
		wf.send_email_alert = 1
		workflow_validate(wf)
		self.assertEqual(wf.send_email_alert, 0)
