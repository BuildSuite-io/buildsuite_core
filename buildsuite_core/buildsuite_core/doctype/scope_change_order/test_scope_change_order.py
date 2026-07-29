# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the Scope Change Order approval flow (approve/reject/revise) and
its BOQ-revision tie-in (api/sco.py). Not part of the M1/M2 manual UAT matrix —
added as extra coverage at the user's request for a feature the gap-analysis
document doesn't track."""

import frappe

from buildsuite_core.api import sco as api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestScopeChangeOrder(BuildSuiteTestCase):
	def _make_sco(self, project, **kw):
		fields = {
			"doctype": "Scope Change Order",
			"project": project,
			"title": f"UAT SCO {self._n}",
			"reason": "UAT",
		}
		fields.update(kw)
		return frappe.get_doc(fields).insert(ignore_permissions=True)

	def _make_boq(self, project):
		return frappe.get_doc(
			{"doctype": "BOQ", "project": project, "title": "Base", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)

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

	# --- creation defaults -------------------------------------------------
	def test_sco_creation_defaults(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		self.assertEqual(sco.status, "Pending Approval")
		self.assertEqual(sco.raised_by, frappe.session.user)
		self.assertEqual(frappe.utils.getdate(sco.raised_date), frappe.utils.getdate())
		self.assertEqual(sco.company, self.company)

	# --- approve -------------------------------------------------------------
	def test_approve_sco_stamps_approver_and_date(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		status = api.approve_sco(sco.name)
		self.assertEqual(status, "Approved")
		sco.reload()
		self.assertEqual(sco.status, "Approved")
		self.assertEqual(sco.approved_by, frappe.session.user)
		self.assertEqual(sco.approved_date, frappe.utils.getdate())
		self.assertEqual(len(sco.scope_change_order_activity), 1)
		self.assertEqual(sco.scope_change_order_activity[0].action, "Approved")

	def test_approve_sco_requires_pending_status(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		api.approve_sco(sco.name)
		with self.assertRaises(frappe.ValidationError):
			api.approve_sco(sco.name)  # already Approved

	def test_approve_sco_rejects_non_governance_role(self):
		# BuildSuite QS has full base DocPerm on this doctype (SCO_ROLE_PERMS)
		# but is NOT in BOQ_APPROVE_ROLES — isolates the api/sco.py governance
		# gate from plain DocPerm (a Foreman would fail earlier, with no
		# DocPerm at all).
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		qs = self._make_persona_user("Quantity Surveyor", "scoqs")
		frappe.set_user(qs)
		try:
			self.assertRaises(frappe.PermissionError, api.approve_sco, sco.name)
		finally:
			frappe.set_user("Administrator")

	# --- reject --------------------------------------------------------------
	def test_reject_sco_records_reason(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		status = api.reject_sco(sco.name, reason="Not in budget")
		self.assertEqual(status, "Rejected")
		sco.reload()
		self.assertEqual(sco.rejection_reason, "Not in budget")
		self.assertEqual(sco.scope_change_order_activity[0].action, "Rejected")

	def test_reject_sco_requires_pending_status(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		api.reject_sco(sco.name, reason="x")
		with self.assertRaises(frappe.ValidationError):
			api.reject_sco(sco.name, reason="y")  # already Rejected

	# --- revise --------------------------------------------------------------
	def test_revise_sco_reopens_for_pending_approval(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)
		api.approve_sco(sco.name)
		status = api.revise_sco(sco.name)
		self.assertEqual(status, "Pending Approval")
		sco.reload()
		self.assertIsNone(sco.approved_by)
		self.assertIsNone(sco.approved_date)
		self.assertIsNone(sco.rejection_reason)
		actions = [a.action for a in sco.scope_change_order_activity]
		self.assertEqual(actions, ["Approved", "Revised"])

	def test_revise_sco_requires_approved_or_rejected(self):
		p = self._make_project(company=self.company)
		sco = self._make_sco(p.name)  # still Pending Approval
		with self.assertRaises(frappe.ValidationError):
			api.revise_sco(sco.name)

	# --- create_boq_revision ---------------------------------------------------
	def test_create_boq_revision_from_approved_sco(self):
		p = self._make_project(company=self.company)
		b = self._make_boq(p.name)
		sco = self._make_sco(p.name)
		api.approve_sco(sco.name)

		res = api.create_boq_revision(sco.name)
		sco.reload()
		self.assertEqual(res["boq"], sco.boq_revision)
		new_boq = frappe.get_doc("BOQ", res["boq"])
		self.assertEqual(new_boq.status, "Draft")
		self.assertEqual(new_boq.base_revision, b.name)

	def test_create_boq_revision_requires_approved_status(self):
		p = self._make_project(company=self.company)
		self._make_boq(p.name)
		sco = self._make_sco(p.name)  # still Pending Approval
		with self.assertRaises(frappe.ValidationError):
			api.create_boq_revision(sco.name)

	def test_create_boq_revision_blocked_when_already_raised(self):
		p = self._make_project(company=self.company)
		self._make_boq(p.name)
		sco = self._make_sco(p.name)
		api.approve_sco(sco.name)
		api.create_boq_revision(sco.name)
		with self.assertRaises(frappe.ValidationError):
			api.create_boq_revision(sco.name)  # a revision was already raised

	def test_create_boq_revision_requires_existing_boq(self):
		p = self._make_project(company=self.company)  # no BOQ on this project
		sco = self._make_sco(p.name)
		api.approve_sco(sco.name)
		with self.assertRaises(frappe.ValidationError):
			api.create_boq_revision(sco.name)
