# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Scope Change Order approval workflow + its activity audit trail."""

import frappe

from buildsuite_core.api.sco import approve_sco, reject_sco, revise_sco
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestScopeChangeOrder(BuildSuiteTestCase):
	def _make_sco(self):
		project = self._make_project(company=self.company)
		return frappe.get_doc(
			{
				"doctype": "Scope Change Order",
				"project": project.name,
				"title": f"SCO {self._n}",
				"type": "Design Change",
				"status": "Pending Approval",
			}
		).insert(ignore_permissions=True)

	def test_activity_log_records_each_transition(self):
		sco = self._make_sco()
		reject_sco(sco.name, "needs costing")
		revise_sco(sco.name)
		approve_sco(sco.name)

		doc = frappe.get_doc("Scope Change Order", sco.name)
		rows = doc.scope_change_order_activity
		self.assertEqual(
			[(r.action, r.comment) for r in rows],
			[("Rejected", "needs costing"), ("Revised", None), ("Approved", None)],
		)
		# every entry stamps who + when
		self.assertTrue(all(r.user == "Administrator" for r in rows))
		self.assertTrue(all(r.activity_on for r in rows))


class TestScopeChangeOrderPermissions(BuildSuiteTestCase):
	"""The 12-persona SCO role matrix (setup.py SCO_ROLE_PERMS + permissions/sco.py)."""

	def _user(self, persona, prefix):
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

	def _sco(self, owner=None):
		h = frappe.generate_hash(length=6)
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"SCO Perm {h}",
				"custom_project_id": f"SCOP-{h}",
				"project_status": "Ongoing",
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		doc = frappe.get_doc(
			{
				"doctype": "Scope Change Order",
				"project": project.name,
				"title": f"SCO {h}",
				"type": "Design Change",
				"status": "Pending Approval",
			}
		).insert(ignore_permissions=True)
		if owner:
			frappe.db.set_value("Scope Change Order", doc.name, "owner", owner)
		return doc

	def _as(self, user, fn):
		frappe.set_user(user)
		try:
			return fn()
		finally:
			frappe.set_user("Administrator")

	def test_estimator_is_read_only(self):
		est = self._user("Estimator", "est")
		sco = self._sco()

		def checks():
			self.assertTrue(frappe.has_permission("Scope Change Order", "read", doc=sco.name))
			self.assertFalse(frappe.has_permission("Scope Change Order", "create"))
			self.assertFalse(frappe.has_permission("Scope Change Order", "write", doc=sco.name))

		self._as(est, checks)

	def test_foreman_has_no_access(self):
		fm = self._user("Foreman / Supervisor", "fm")
		sco = self._sco()
		self._as(
			fm,
			lambda: self.assertFalse(
				frappe.has_permission("Scope Change Order", "read", doc=sco.name)
			),
		)

	def test_qs_is_full(self):
		qs = self._user("Quantity Surveyor", "qs")
		sco = self._sco()

		def checks():
			self.assertTrue(frappe.has_permission("Scope Change Order", "create"))
			self.assertTrue(frappe.has_permission("Scope Change Order", "write", doc=sco.name))
			self.assertTrue(frappe.has_permission("Scope Change Order", "delete", doc=sco.name))

		self._as(qs, checks)

	def test_site_engineer_create_own_scope(self):
		se = self._user("Site Engineer", "se")
		others = self._sco()  # owned by Administrator
		mine = self._sco(owner=se)

		def checks():
			self.assertTrue(frappe.has_permission("Scope Change Order", "create"))
			# read only their OWN change orders
			self.assertTrue(frappe.has_permission("Scope Change Order", "read", doc=mine.name))
			self.assertFalse(frappe.has_permission("Scope Change Order", "read", doc=others.name))
			# CR only — no write/delete even on their own
			self.assertFalse(frappe.has_permission("Scope Change Order", "write", doc=mine.name))

		self._as(se, checks)

	def test_site_engineer_cannot_approve(self):
		se = self._user("Site Engineer", "se2")
		sco = self._sco(owner=se)

		def attempt():
			with self.assertRaises(frappe.PermissionError):
				approve_sco(sco.name)

		self._as(se, attempt)
