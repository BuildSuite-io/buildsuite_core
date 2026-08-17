# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestExpenseEntry(IntegrationTestCase):
	"""
	Integration tests for ExpenseEntry.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestExpenseEntry(BuildSuiteTestCase):
	"""Expense Entry: doctype validate() guards + description auto-build, and the
	api/expense_entry.py endpoints (save/submit/cancel/list/get/context/pickers)."""

	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name
		from buildsuite_core.utils.petty_cash import resolve_petty_cash_account

		self.petty = resolve_petty_cash_account(self.company)
		self.user = self._make_user()
		self.employee = self._make_employee(self.user)

	# --- fixtures --------------------------------------------------------
	def _make_user(self):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"ee-{self._n}@example.com",
					"first_name": "EE Holder",
					"send_welcome_email": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _make_employee(self, user_id):
		try:
			return (
				frappe.get_doc(
					{
						"doctype": "Employee",
						"first_name": f"EE Holder {self._n}",
						"employee_name": f"EE Holder {self._n}",
						"company": self.company,
						"status": "Active",
						"date_of_joining": "2020-01-01",
						"date_of_birth": "1990-01-01",
						"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
						"user_id": user_id,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		except Exception as e:  # HR not configured on the site — skip the suite cleanly
			self.skipTest(f"cannot create Employee: {e}")

	def _account(self, name, root_type, account_type, parent):
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, name, root_type, account_type, parent)

	def _bank(self):
		return self._account("Cash", "Asset", "Cash", "Current Assets")

	def _expense_account(self):
		return self._account("Site Expenses", "Expense", "Expense Account", "Expenses")

	def _expense_entry(self, amount=1000, submit=False, paid_from="Petty Cash", rows=None):
		if paid_from == "Company":
			account = self._bank()
			employee = None
		else:
			account = self.petty
			employee = self.employee
		if rows is None:
			rows = [
				{
					"employee": employee,
					"payment_account": account,
					"expense_account": self._expense_account(),
					"project": self.project,
					"amount": amount,
					"description": "Diesel",
				}
			]
		doc = frappe.get_doc(
			{
				"doctype": "Expense Entry",
				"date": "2026-07-21",
				"company": self.company,
				"project": self.project,
				"employee": employee,
				"payment_account": account,
				"paid_from": paid_from,
				"expense_entry_table": rows,
			}
		).insert(ignore_permissions=True)
		if submit:
			doc.submit()
		return doc

	# --- A: doctype validate() guards ---------------------------------------
	def test_requires_at_least_one_row(self):
		with self.assertRaises(frappe.ValidationError):
			self._expense_entry(rows=[])

	def test_row_requires_positive_amount_and_accounts(self):
		base_row = {
			"employee": self.employee,
			"payment_account": self.petty,
			"expense_account": self._expense_account(),
			"project": self.project,
			"amount": 1000,
			"description": "x",
		}
		with self.assertRaises(frappe.ValidationError):
			self._expense_entry(rows=[{**base_row, "amount": 0}])

		row_no_expense = {k: v for k, v in base_row.items() if k != "expense_account"}
		with self.assertRaises(frappe.ValidationError):
			self._expense_entry(rows=[row_no_expense])

		row_no_payment = {k: v for k, v in base_row.items() if k != "payment_account"}
		with self.assertRaises(frappe.ValidationError):
			self._expense_entry(rows=[row_no_payment])

	def test_description_auto_generated_and_stamped_on_edit(self):
		ee = self._expense_entry(amount=1000)  # no explicit description -> auto-built
		auto_built = ee.description
		self.assertTrue(auto_built)
		self.assertIn("1000", auto_built)  # build_description() includes the amount

		ee.description = "Fuel for generator"
		ee.save(ignore_permissions=True)
		ee.reload()
		self.assertIn("Fuel for generator", ee.description)
		self.assertIn("Updated by", ee.description)

	def test_cancel_submitted_expense_reverses_je(self):
		ee = self._expense_entry(amount=2000, submit=True)
		je = ee.journal_entry
		self.assertTrue(je)
		ee.cancel()
		self.assertEqual(frappe.db.get_value("Journal Entry", je, "docstatus"), 2)
		ee.reload()
		self.assertFalse(ee.journal_entry)

	# --- B: api/expense_entry.py — save / submit / cancel / list / get ------
	def test_save_expense_petty_cash_pins_caller_as_holder(self):
		import json

		from buildsuite_core.api.expense_entry import save_expense

		frappe.set_user(self.user)
		try:
			res = save_expense(
				json.dumps(
					{
						"project": self.project,
						"paid_from": "petty",
						"rows": [{"expense_account": self._expense_account(), "amount": 500, "description": "Fuel"}],
					}
				)
			)
		finally:
			frappe.set_user("Administrator")

		doc = frappe.get_doc("Expense Entry", res["name"])
		self.assertEqual(doc.employee, self.employee)
		self.assertEqual(doc.paid_from, "Petty Cash")
		self.assertEqual(doc.docstatus, 0)

	def test_save_expense_company_mode_requires_account(self):
		import json

		from buildsuite_core.api.expense_entry import save_expense

		with self.assertRaises(frappe.ValidationError):
			save_expense(
				json.dumps(
					{
						"project": self.project,
						"paid_from": "company",
						"rows": [{"expense_account": self._expense_account(), "amount": 500}],
					}
				)
			)  # no company_account supplied

		bank = self._bank()
		res = save_expense(
			json.dumps(
				{
					"project": self.project,
					"paid_from": "company",
					"company_account": bank,
					"rows": [{"expense_account": self._expense_account(), "amount": 500}],
				}
			)
		)
		doc = frappe.get_doc("Expense Entry", res["name"])
		self.assertEqual(doc.paid_from, "Company")
		self.assertFalse(doc.employee)
		self.assertEqual(doc.payment_account, bank)

	def test_save_expense_edit_only_while_draft(self):
		import json

		from buildsuite_core.api.expense_entry import save_expense

		# Administrator already holds the approver role, so the explicit `employee`
		# override is honoured here (see api/expense_entry.py save_expense).
		res = save_expense(
			json.dumps(
				{
					"project": self.project,
					"paid_from": "petty",
					"employee": self.employee,
					"rows": [{"expense_account": self._expense_account(), "amount": 500}],
				}
			)
		)
		doc = frappe.get_doc("Expense Entry", res["name"])
		doc.submit()

		with self.assertRaises(frappe.ValidationError):
			save_expense(
				json.dumps(
					{
						"name": res["name"],
						"project": self.project,
						"paid_from": "petty",
						"employee": self.employee,
						"rows": [{"expense_account": self._expense_account(), "amount": 999}],
					}
				)
			)

	def test_submit_expense_posts_je_and_requires_draft(self):
		from buildsuite_core.api.expense_entry import submit_expense

		ee = self._expense_entry(amount=1200)
		out = submit_expense(ee.name)
		self.assertTrue(out["journal_entry"])
		ee.reload()
		self.assertEqual(ee.docstatus, 1)

		with self.assertRaises(frappe.ValidationError):
			submit_expense(ee.name)  # already submitted

	def test_cancel_expense_cancels_submitted_or_deletes_draft(self):
		from buildsuite_core.api.expense_entry import cancel_expense

		submitted = self._expense_entry(amount=1000, submit=True)
		out1 = cancel_expense(submitted.name)
		self.assertTrue(out1["cancelled"])
		self.assertEqual(frappe.db.get_value("Expense Entry", submitted.name, "docstatus"), 2)

		draft = self._expense_entry(amount=500)
		out2 = cancel_expense(draft.name)
		self.assertTrue(out2["deleted"])
		self.assertFalse(frappe.db.exists("Expense Entry", draft.name))

	def test_list_and_get_expense_endpoints(self):
		from buildsuite_core.api.expense_entry import get_expense, list_expenses

		ee = self._expense_entry(amount=750)
		listed = list_expenses()
		row = next((r for r in listed if r["name"] == ee.name), None)
		self.assertIsNotNone(row)
		self.assertEqual(flt(row["amount"]), 750)
		self.assertEqual(row["status"], "Draft")

		detail = get_expense(ee.name)
		self.assertEqual(flt(detail["total_amount"]), 750)
		self.assertEqual(len(detail["rows"]), 1)
		self.assertEqual(detail["rows"][0]["expense_account"], self._expense_account())

	# --- C: other read-only endpoints ---------------------------------------
	def test_context_reports_employee_balances(self):
		from buildsuite_core.api.expense_entry import context

		req = frappe.get_doc(
			{
				"doctype": "Petty Cash Request",
				"project": self.project,
				"request_date": "2026-07-20",
				"amount": 5000,
				"purpose": "Float",
				"requested_by": self.user,
			}
		).insert(ignore_permissions=True)
		req.disburse(self._bank())

		frappe.set_user(self.user)
		try:
			out = context()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(out["employee"], self.employee)
		self.assertEqual(flt(out["approved"]), 5000)
		self.assertEqual(flt(out["available"]), 5000)

	def test_list_cash_bank_accounts_excludes_petty_cash(self):
		from buildsuite_core.api.expense_entry import list_cash_bank_accounts

		accounts = list_cash_bank_accounts(project=self.project)
		names = [a["name"] for a in accounts]
		self.assertNotIn(self.petty, names)
		for a in accounts:
			self.assertIn(a["account_type"], ("Bank", "Cash"))

	def test_list_expense_accounts_returns_expense_type_only(self):
		from buildsuite_core.api.expense_entry import list_expense_accounts

		acct = self._expense_account()
		accounts = list_expense_accounts(self.company)
		names = [a["name"] for a in accounts]
		self.assertIn(acct, names)
		self.assertNotIn(self.petty, names)  # Petty Cash is an Asset account, not Expense
