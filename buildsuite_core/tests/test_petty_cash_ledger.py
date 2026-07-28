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

	def _expense_entry(self, amount, submit=False, paid_from="Petty Cash", cost_type="Overhead"):
		# PF-04: Petty Cash → Cr the holder's float (holder stamped); Company → Cr a
		# Bank/Cash account, no holder.
		if paid_from == "Company":
			account = self._bank()
			employee = None
		else:
			account = self.petty
			employee = self.employee
		doc = frappe.get_doc(
			{
				"doctype": "Expense Entry",
				"date": "2026-07-21",
				"company": self.company,
				"project": self.project,
				"employee": employee,
				"payment_account": account,
				"paid_from": paid_from,
				"expense_entry_table": [
					{
						"employee": employee,
						"payment_account": account,
						"expense_account": self._expense_account(),
						"cost_type": cost_type,
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

	def test_cost_type_stored(self):
		ee = self._expense_entry(1000, cost_type="Material")
		self.assertEqual(ee.expense_entry_table[0].cost_type, "Material")

	def test_holder_required_for_petty_cash(self):
		# PF-04: petty-cash spend must name the holder whose float it draws down.
		doc = frappe.get_doc(
			{
				"doctype": "Expense Entry",
				"date": "2026-07-21",
				"company": self.company,
				"project": self.project,
				"employee": None,
				"payment_account": self.petty,
				"paid_from": "Petty Cash",
				"expense_entry_table": [
					{
						"payment_account": self.petty,
						"expense_account": self._expense_account(),
						"cost_type": "Overhead",
						"project": self.project,
						"amount": 500,
						"description": "No holder",
					}
				],
			}
		)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_company_paid_expense_carries_no_holder(self):
		self._disburse(10000)
		# Company-paid spend Crs a Bank/Cash account, not the holder's float, so the
		# petty balance is untouched and the credit leg carries no employee.
		ee = self._expense_entry(2000, submit=True, paid_from="Company")
		self.assertEqual(flt(pc.get_balance_amount_approved(self.employee)), 10000)
		mine = [r for r in pc.reconciled_holder_balances(self.company) if r["employee"] == self.employee][0]
		self.assertEqual(flt(mine["spent"]), 0)
		# The submitted expense forced the holder off entirely (Company mode).
		self.assertFalse(ee.employee)

	def test_own_pocket_pushes_petty_balance_negative(self):
		# PF-04: with no float disbursed, petty-cash spend simply drives the holder's
		# balance negative — the amount owed back to them ("owed to holder").
		self._expense_entry(2000, submit=True, paid_from="Petty Cash")
		self.assertEqual(flt(pc.get_balance_amount_approved(self.employee)), -2000)
		mine = [r for r in pc.reconciled_holder_balances(self.company) if r["employee"] == self.employee][0]
		self.assertEqual(flt(mine["balance"]), -2000)
		# A later disbursement settles the negative balance.
		self._disburse(5000)
		self.assertEqual(flt(pc.get_balance_amount_approved(self.employee)), 3000)
