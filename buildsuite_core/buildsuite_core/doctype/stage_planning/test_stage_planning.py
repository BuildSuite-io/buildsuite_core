# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.model.workflow import apply_workflow

from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.buildsuite_core.doctype.stage_planning.stage_planning import (
	reject_stage_planning,
	revise_stage_planning,
	get_stage_activity,
)


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestStagePlanning(IntegrationTestCase):
	pass


class TestStagePlanning(BuildSuiteTestCase):
	"""Stage Planning approval workflow: own-scope submit, revise-clone of a
	rejected stage (SAW-006), approved-edit lock (SAW-011), and activity log
	(SAW-013)."""

	def _make_stage(self, project, task=None, state="Draft"):
		rows = [{"task": task, "planned_qty": 80, "qty_unit": "%"}] if task else []
		return frappe.get_doc({
			"doctype": "Stage Planning",
			"stage_name": f"ST {frappe.generate_hash(length=4)}",
			"project": project,
			"workflow_state": state,
			"stage_planning_tasks": rows,
		}).insert(ignore_permissions=True)

	def _approve(self, st):
		apply_workflow(st, "Submit for Approval")
		apply_workflow(st, "Approve")
		st.reload()

	def test_site_engineer_submits_own_stage_planning(self):
		"""PRM-010 — a Site Engineer can submit their OWN Draft stage. The
		own-scope write gate checks the PERSISTED state, not the in-memory one,
		so submit (which sets the next state before saving) doesn't self-lock."""
		se = f"se-{self._n}@example.com"
		frappe.get_doc({
			"doctype": "User", "email": se, "first_name": "SE",
			"send_welcome_email": 0, "user_type": "System User",
			"persona": "Site Engineer", "company": self.company,
		}).insert(ignore_permissions=True)

		p = frappe.get_doc({
			"doctype": "Project", "project_name": f"WF {self._n}",
			"custom_project_id": f"WF-{self._n}", "project_status": "Ongoing",
			"company": self.company, "custom_team_members": [{"user": se}],
		}).insert(ignore_permissions=True)

		frappe.set_user(se)
		try:
			st = frappe.get_doc({
				"doctype": "Stage Planning", "stage_name": f"WF {self._n}",
				"project": p.name, "workflow_state": "Draft",
			}).insert()
			apply_workflow(st, "Submit for Approval")
			st.reload()
			self.assertEqual(st.workflow_state, "Pending Approval")

			# Once submitted, the SE can no longer edit their own (now locked) stage.
			st.stage_name = "should not save"
			self.assertRaises(frappe.PermissionError, st.save)
		finally:
			frappe.set_user("Administrator")

	def test_revise_clones_rejected_stage(self):
		"""SAW-006 — revising a Rejected stage clones it into a fresh Draft and
		leaves the original Rejected stage untouched (audit record)."""
		p = self._make_project()
		t = self._make_task(p.name)
		st = self._make_stage(p.name, task=t.name)
		apply_workflow(st, "Submit for Approval")
		reject_stage_planning(st.name, "Scope unclear")
		st.reload()
		self.assertEqual(st.workflow_state, "Rejected")

		res = revise_stage_planning(st.name)
		clone = frappe.get_doc("Stage Planning", res["name"])
		self.assertNotEqual(clone.name, st.name)
		self.assertEqual(clone.workflow_state, "Draft")
		self.assertFalse(clone.reject_reason)
		self.assertEqual(len(clone.stage_planning_tasks), 1)
		self.assertEqual(clone.stage_planning_tasks[0].task, t.name)
		# Original stays Rejected.
		st.reload()
		self.assertEqual(st.workflow_state, "Rejected")

	def test_approved_stage_task_edit_throws(self):
		"""SAW-011 — an Approved stage's task list / planned qty is locked."""
		p = self._make_project()
		t = self._make_task(p.name)
		st = self._make_stage(p.name, task=t.name)
		self._approve(st)
		st.stage_planning_tasks[0].planned_qty = 50
		self.assertRaises(frappe.ValidationError, lambda: st.save(ignore_permissions=True))

	def test_approved_to_draft_allows_task_change(self):
		"""SAW-011 — Revise (Approved -> Draft) reopens editing."""
		p = self._make_project()
		t = self._make_task(p.name)
		st = self._make_stage(p.name, task=t.name)
		self._approve(st)
		apply_workflow(st, "Revise")
		st.reload()
		self.assertEqual(st.workflow_state, "Draft")
		st.stage_planning_tasks[0].planned_qty = 50
		st.save(ignore_permissions=True)  # must not raise
		st.reload()
		self.assertEqual(st.stage_planning_tasks[0].planned_qty, 50)

	def test_stage_transition_logs_activity(self):
		"""SAW-013 — each workflow transition is recorded on the timeline."""
		p = self._make_project()
		st = self._make_stage(p.name)
		apply_workflow(st, "Submit for Approval")
		types = [a["type"] for a in get_stage_activity(st.name)]
		self.assertIn("created", types)
		self.assertIn("submitted", types)
