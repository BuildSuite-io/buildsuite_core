# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Bank & Cash Accounts setting (S229) — the finance-account master CRUD."""

import frappe

from buildsuite_core.api import finance_account as fa
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestFinanceAccount(BuildSuiteTestCase):
	def test_create_list_delete(self):
		rec = fa.save_finance_account(name=f"UAT Cash {self._n}", type="Cash", opening_balance=1000)
		self.assertEqual(rec["type"], "Cash")
		self.assertEqual(rec["opening_balance"], 1000)
		# No movements yet, so current balance == opening balance.
		self.assertEqual(rec["current_balance"], 1000)

		listed = fa.list_finance_accounts()
		self.assertIn(rec["id"], [a["id"] for a in listed])

		self.assertEqual(fa.delete_finance_account(rec["id"]), {"ok": True})
		self.assertNotIn(rec["id"], [a["id"] for a in fa.list_finance_accounts()])

	def test_account_no_persists_for_bank(self):
		rec = fa.save_finance_account(
			name=f"UAT Bank {self._n}", type="Bank", account_no="998877", opening_balance=0
		)
		try:
			self.assertEqual(rec["account_no"], "998877")
			self.assertEqual(rec["type"], "Bank")
		finally:
			fa.delete_finance_account(rec["id"])

	def test_non_finance_role_cannot_manage(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"fa-se-{self._n}@example.com",
				"first_name": "FA SE",
				"send_welcome_email": 0,
				"user_type": "System User",
				"persona": "Site Engineer",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

		frappe.set_user(user.name)
		try:
			self.assertRaises(
				frappe.PermissionError,
				fa.save_finance_account,
				name=f"Blocked {self._n}",
				type="Cash",
			)
		finally:
			frappe.set_user("Administrator")
