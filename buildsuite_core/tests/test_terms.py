# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Terms & Conditions library: the admin / Accountant / Procurement Officer / Estimator roles
manage the native Terms and Conditions doctype; every other role gets select-only."""

import frappe

from buildsuite_core.api.terms import list_terms, save_terms, terms_access
from buildsuite_core.permissions.setup import setup_terms_permissions
from buildsuite_core.tests.base import BuildSuiteTestCase

DOCTYPE = "Terms and Conditions"
FULL = (
	"BuildSuite Administrator",
	"BuildSuite Accountant",
	"BuildSuite Procurement Officer",
	"BuildSuite Estimator",
)
SELECT = ("BuildSuite PM", "BuildSuite Site Engineer", "BuildSuite Director", "BuildSuite Store Keeper")


class TestTerms(BuildSuiteTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		setup_terms_permissions()
		frappe.db.commit()

	def _user(self, role):
		email = f"terms-{frappe.generate_hash(length=5)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Terms",
				"user_type": "System User",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
		return email

	def test_full_roles_manage(self):
		for role in FULL:
			u = self._user(role)
			self.assertTrue(frappe.has_permission(DOCTYPE, "read", user=u), f"{role} read")
			self.assertTrue(frappe.has_permission(DOCTYPE, "write", user=u), f"{role} write")
			self.assertTrue(frappe.has_permission(DOCTYPE, "create", user=u), f"{role} create")
			self.assertTrue(frappe.has_permission(DOCTYPE, "delete", user=u), f"{role} delete")

	def test_rest_are_select_only(self):
		for role in SELECT:
			u = self._user(role)
			self.assertTrue(frappe.has_permission(DOCTYPE, "select", user=u), f"{role} select")
			self.assertFalse(frappe.has_permission(DOCTYPE, "read", user=u), f"{role} NOT read")
			self.assertFalse(frappe.has_permission(DOCTYPE, "write", user=u), f"{role} NOT write")

	def test_save_list_access_for_a_full_role(self):
		est = self._user("BuildSuite Estimator")
		frappe.set_user(est)
		try:
			res = save_terms(
				title=f"Clause {frappe.generate_hash(length=4)}",
				applicable_for="Quotation",
				terms="<p>Valid <b>30</b> days.</p><table><tbody><tr><td>a</td></tr></tbody></table>",
			)
			self.assertTrue(res["name"])
			acc = terms_access()
			self.assertTrue(acc["can_write"])
			self.assertIn("Quotation", acc["applicable_for"])
			stored = frappe.db.get_value(
				DOCTYPE, res["name"], ["custom_applicable_for", "terms"], as_dict=True
			)
			self.assertEqual(stored.custom_applicable_for, "Quotation")
			self.assertIn("<table>", stored.terms)  # rich text / table preserved
			self.assertIn(res["name"], [r["name"] for r in list_terms()])
		finally:
			frappe.set_user("Administrator")

	def test_select_only_user_gets_empty_library(self):
		pm = self._user("BuildSuite PM")
		frappe.set_user(pm)
		try:
			self.assertFalse(terms_access()["can_read"])
			self.assertEqual(list_terms(), [])  # no read perm → empty, not a 403
		finally:
			frappe.set_user("Administrator")
