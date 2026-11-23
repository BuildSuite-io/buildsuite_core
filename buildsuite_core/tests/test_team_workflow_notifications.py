# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Team-scoped workflow notifications (Project Settings): for a listed document type, the next
step's role holders on the project team are notified; nobody of that role on the team → all of
them; a document type not listed → no team notification."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.team_workflow_notifications import clear_cache

SCO = "Scope Change Order"


class TestTeamScopedWorkflowNotifications(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		if not frappe.db.get_value("Workflow", {"document_type": SCO, "is_active": 1}):
			self.skipTest("no active Scope Change Order workflow on this site")
		self.pm_team = self._pm("team")
		self.pm_other = self._pm("other")
		self.addCleanup(clear_cache)

	def _pm(self, tag):
		email = f"twn-{tag}-{self._n}-{frappe.generate_hash(length=5)}@example.com"
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": f"PM {tag}", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		user.add_roles("BuildSuite PM")
		return email

	def _scope(self, doctypes):
		settings = frappe.get_single("Project Settings")
		settings.set("team_scoped_workflows", [{"document_type": d} for d in doctypes])
		settings.flags.ignore_permissions = True
		settings.save()  # clears the cached list

	def _raise_sco(self, team=()):
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"TWN {frappe.generate_hash(length=6)}",
				"company": self.company,
				"custom_team_members": [{"user": u} for u in team],
			}
		).insert(ignore_permissions=True)
		return frappe.get_doc(
			{"doctype": SCO, "project": project.name, "title": "Extra lighting", "reason": "Client request"}
		).insert(ignore_permissions=True)

	def _notified(self, user, sco):
		return bool(
			frappe.db.exists(
				"Notification Log", {"for_user": user, "document_type": SCO, "document_name": sco.name}
			)
		)

	def test_only_the_project_team_is_notified(self):
		self._scope([SCO])
		sco = self._raise_sco(team=[self.pm_team])
		self.assertTrue(self._notified(self.pm_team, sco))
		self.assertFalse(self._notified(self.pm_other, sco))

	def test_everyone_with_the_role_when_nobody_on_the_team_has_it(self):
		self._scope([SCO])
		sco = self._raise_sco(team=[])
		self.assertTrue(self._notified(self.pm_team, sco))
		self.assertTrue(self._notified(self.pm_other, sco))

	def test_a_document_type_not_listed_is_left_alone(self):
		self._scope([])
		sco = self._raise_sco(team=[self.pm_team])
		self.assertFalse(self._notified(self.pm_team, sco))
		self.assertFalse(self._notified(self.pm_other, sco))
