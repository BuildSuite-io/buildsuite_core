# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Employee petty-cash ledger — Expense Entry spend + the balance / transaction
endpoints in utils.petty_cash, and the reconciliation that tags the holder
Employee on a Petty Cash Request disbursement so issued float and later spend
share one ledger."""

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils import petty_cash as pc


class TestPettyCashLedger(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name
		self.petty = pc.resolve_petty_cash_account(self.company)
		self.user = self._make_user()
		self.employee = self._make_employee(self.user)

	# --- fixtures --------------------------------------------------------
	def _make_user(self):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": f"pc-{self._n}@example.com",
				"first_name": "PC Holder",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True).name

	def _make_employee(self, user_id):
		try:
			return frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": f"PC Holder {self._n}",
					"employee_name": f"PC Holder {self._n}",
					"company": self.company,
					"status": "Active",
					"date_of_joining": "2020-01-01",
					"date_of_birth": "1990-01-01",
					"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
					"user_id": user_id,
				}
			).insert(ignore_permissions=True).name
		except Exception as e:  # HR not configured on the site — skip the suite cleanly
			self.skipTest(f"cannot create Employee: {e}")

	def _account(self, name, root_type, account_type, parent):
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, name, root_type, account_type, parent)

	def _bank(self):
		return self._account("Cash", "Asset", "Cash", "Current Assets")

	def _expense_account(self):
		return self._account("Site Expenses", "Expense", "Expense Account", "Expenses")

	def _disburse(self, amount):
		req = frappe.get_doc(
			{
				"doctype": "Petty Cash Request",
				"project": self.project,
				"request_date": "2026-07-20",
				"amount": amount,
				"purpose": "Float",
				"requested_by": self.user,
			}
		).insert(ignore_permissions=True)
		req.disburse(self._bank())
		return req

	def _expense_entry(self, amount, submit=False):
		doc = frappe.get_doc(
			{
				"doctype": "Expense Entry",
				"date": "2026-07-21",
				"company": self.company,
				"project": self.project,
				"employee": self.employee,
				"payment_account": self.petty,
				"expense_entry_table": [
					{
						"employee": self.employee,
						"payment_account": self.petty,
						"expense_account": self._expense_account(),
						"project": self.project,
						"amount": amount,
						"description": "Diesel",
					}
				],
			}
		).insert(ignore_permissions=True)
		if submit:
			doc.submit()
		return doc

	# --- tests -----------------------------------------------------------
	def test_disburse_tags_employee_on_ledger(self):
		self._disburse(10000)
		# Issued float debits the employee's Petty Cash → shows as approved balance.
		self.assertEqual(flt(pc.get_balance_amount_approved(self.employee)), 10000)

	def test_pending_vs_approved_balance(self):
		self._disburse(10000)
		# A draft Expense Entry is "pending approval" and not yet in the GL balance.
		self._expense_entry(3000, submit=False)
		self.assertEqual(flt(pc.get_pending_approval_balance(self.employee)), 3000)
		self.assertEqual(flt(pc.get_balance_amount_approved(self.employee)), 10000)
		# include-review nets drafts out: 10000 posted − 3000 pending.
		self.assertEqual(flt(pc.get_total_balance_include_review(self.employee)), 7000)

	def test_submitted_expense_reduces_approved_balance(self):
		self._disburse(10000)
		ee = self._expense_entry(3000, submit=True)
		self.assertTrue(ee.journal_entry)
		# Submitting posts Cr Petty Cash → approved balance drops, nothing pending.
		self.assertEqual(flt(pc.get_pending_approval_balance(self.employee)), 0)
		self.assertEqual(flt(pc.get_balance_amount_approved(self.employee)), 7000)

	def test_transaction_list_running_balance(self):
		self._disburse(10000)
		self._expense_entry(3000, submit=True)
		rows = pc.get_transaction_list(self.employee)
		self.assertEqual(len(rows), 2)
		# Newest first; the latest row's running balance is the net position.
		self.assertEqual(flt(rows[0]["balance"]), 7000)

	def test_reconciled_holder_balances(self):
		self._disburse(10000)
		self._expense_entry(3000, submit=True)
		rows = pc.reconciled_holder_balances(self.company)
		mine = [r for r in rows if r["employee"] == self.employee]
		self.assertEqual(len(mine), 1)
		self.assertEqual(flt(mine[0]["disbursed"]), 10000)
		self.assertEqual(flt(mine[0]["spent"]), 3000)
		self.assertEqual(flt(mine[0]["balance"]), 7000)

	def test_misspelled_alias_matches(self):
		self._disburse(5000)
		self.assertEqual(
			flt(pc.get_total_balance_inculde_review(self.employee)),
			flt(pc.get_total_balance_include_review(self.employee)),
		)
