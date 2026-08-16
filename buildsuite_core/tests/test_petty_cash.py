# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Petty Cash Request → Journal Entry on disburse (the live part of Project Finance)."""

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPettyCash(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self._ensure_employee("Administrator")
		# Petty cash derives company from the requester's Employee, so anchor the whole
		# test (project, disburse account) to that Employee's company.
		self.company = frappe.db.get_value(
			"Employee", {"user_id": "Administrator", "status": "Active"}, "company"
		)
		self.project = self._make_project(company=self.company).name

	def _ensure_employee(self, user_id, company=None):
		existing = frappe.db.get_value("Employee", {"user_id": user_id, "status": "Active"}, "name")
		if existing:
			return existing
		return (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": f"PC {user_id}",
					"employee_name": f"PC {user_id}",
					"company": company or self.company,
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

	def _cash_account(self):
		# A real funding source — a Bank/Cash account that is NOT the Petty Cash account
		# (disbursing "from" Petty Cash is now rejected).
		from buildsuite_core.utils.petty_cash import get_petty_cash_account

		petty = get_petty_cash_account(self.company)
		filters = {"company": self.company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}
		if petty:
			filters["name"] = ["!=", petty]
		acc = frappe.db.get_value("Account", filters, "name")
		if acc:
			return acc
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, "Test Bank", "Asset", "Bank", "Bank Accounts")

	def _request(self, amount=15000, purpose="Diesel + site consumables"):
		return frappe.get_doc(
			{
				"doctype": "Petty Cash Request",
				"request_date": "2026-07-20",
				"amount": amount,
				"purpose": purpose,
			}
		).insert(ignore_permissions=True)

	def test_company_from_employee(self):
		# Petty cash carries no project; company is anchored to the requester's Employee.
		req = self._request()
		emp_company = frappe.db.get_value(
			"Employee", {"user_id": "Administrator", "status": "Active"}, "company"
		)
		self.assertEqual(req.company, emp_company)

	def test_non_employee_cannot_request(self):
		user = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"noemp-{self._n}@example.com",
					"first_name": "NoEmp",
					"send_welcome_email": 0,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		req = frappe.get_doc(
			{
				"doctype": "Petty Cash Request",
				"request_date": "2026-07-20",
				"amount": 1000,
				"purpose": "x",
				"requested_by": user,
			}
		)
		self.assertRaises(frappe.ValidationError, req.insert, ignore_permissions=True)

	def test_disburse_posts_journal_entry(self):
		req = self._request(amount=15000)
		bank = self._cash_account()
		req.disburse(bank)
		req.reload()

		self.assertEqual(req.status, "Disbursed")
		self.assertTrue(req.journal_entry)
		self.assertEqual(req.paid_from, bank)

		je = frappe.get_doc("Journal Entry", req.journal_entry)
		self.assertEqual(je.docstatus, 1)
		debit = [a for a in je.accounts if flt(a.debit_in_account_currency) > 0]
		credit = [a for a in je.accounts if flt(a.credit_in_account_currency) > 0]
		# Imprest treatment: Dr Petty Cash 15000 (holder on the `employee` dimension) / Cr bank 15000.
		self.assertEqual(flt(debit[0].debit_in_account_currency), 15000)
		self.assertEqual(
			debit[0].employee,
			frappe.db.get_value("Employee", {"user_id": "Administrator", "status": "Active"}, "name"),
		)
		self.assertEqual(credit[0].account, bank)
		self.assertEqual(flt(credit[0].credit_in_account_currency), 15000)

	def test_cancel_disbursement_reverses_je(self):
		req = self._request()
		req.disburse(self._cash_account())
		req.reload()
		je = req.journal_entry
		req.cancel_disbursement()
		req.reload()
		self.assertEqual(req.status, "Requested")
		self.assertFalse(req.journal_entry)
		self.assertEqual(frappe.db.get_value("Journal Entry", je, "docstatus"), 2)

	def test_disburse_blocked_when_not_requested(self):
		req = self._request()
		req.disburse(self._cash_account())
		req.reload()
		# Already disbursed — a second disburse must fail.
		self.assertRaises(frappe.ValidationError, req.disburse, self._cash_account())

	def test_disburse_rejects_cross_company_account(self):
		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		other_acc = frappe.db.get_value(
			"Account", {"company": other, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
		)
		if not other_acc:
			self.skipTest("no cross-company cash account")
		req = self._request()
		self.assertRaises(frappe.ValidationError, req.disburse, other_acc)

	def test_disburse_rejects_petty_cash_as_source(self):
		# Cr must be a real funding source — paying "from" Petty Cash would post
		# Dr Petty Cash / Cr Petty Cash (a no-op).
		from buildsuite_core.utils.petty_cash import resolve_petty_cash_account

		petty = resolve_petty_cash_account(self.company)
		req = self._request()
		self.assertRaises(frappe.ValidationError, req.disburse, petty)

	def test_direct_desk_je_disburses_and_stamps_holder(self):
		# Bigger teams post the disbursement Journal Entry by hand in Desk instead of using
		# the app. Linking the JE to the request + submitting must disburse it and stamp the
		# holder on the Petty Cash leg (so the GL/reconciliation attributes the float), even
		# when the accountant left the employee blank.
		from buildsuite_core.utils.petty_cash import resolve_petty_cash_account

		holder = frappe.db.get_value("Employee", {"user_id": "Administrator", "status": "Active"}, "name")
		req = self._request(amount=8000)
		petty = resolve_petty_cash_account(self.company)
		bank = self._cash_account()

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.posting_date = "2026-07-20"
		je.petty_cash_request = req.name
		je.append("accounts", {"account": petty, "debit_in_account_currency": 8000})  # employee left blank
		je.append("accounts", {"account": bank, "credit_in_account_currency": 8000})
		je.flags.ignore_permissions = True
		je.insert()
		je.submit()

		# Holder auto-stamped on the Petty Cash leg → GL carries the employee dimension.
		je.reload()
		petty_line = next(a for a in je.accounts if a.account == petty)
		self.assertEqual(petty_line.employee, holder)
		self.assertEqual(
			frappe.db.get_value(
				"GL Entry", {"voucher_no": je.name, "account": petty, "is_cancelled": 0}, "employee"
			),
			holder,
		)

		# Submitting the JE disbursed the request.
		req.reload()
		self.assertEqual(req.status, "Disbursed")
		self.assertEqual(req.journal_entry, je.name)
		self.assertEqual(req.paid_from, bank)

		# Cancelling the JE reverts it to Requested.
		je.cancel()
		req.reload()
		self.assertEqual(req.status, "Requested")
		self.assertFalse(req.journal_entry)

	def test_disbursement_prefill(self):
		from buildsuite_core.api.petty_cash import disbursement_prefill
		from buildsuite_core.utils.petty_cash import resolve_petty_cash_account

		holder = frappe.db.get_value("Employee", {"user_id": "Administrator", "status": "Active"}, "name")
		req = self._request(amount=6000)
		data = disbursement_prefill(req.name)
		self.assertEqual(data["company"], self.company)
		self.assertEqual(flt(data["amount"]), 6000)
		self.assertEqual(data["petty_cash_account"], resolve_petty_cash_account(self.company))
		self.assertEqual(data["employee"], holder)
		# A disbursed request can't be prefilled for another disbursement.
		req.disburse(self._cash_account())
		self.assertRaises(frappe.ValidationError, disbursement_prefill, req.name)

	def test_direct_issue_creates_disbursed_je(self):
		# S273 — a direct issue creates the request already Disbursed, with no project, and
		# posts a submitted "Petty Cash" Journal Entry linked back to it.
		import json

		from buildsuite_core.api import petty_cash as pc

		bank = self._cash_account()
		rec = pc.issue_direct(
			json.dumps(
				{
					"requested_by": "Administrator",
					"amount": 3000,
					"paid_from": bank,
					"purpose": "Direct float to a site holder",
				}
			)
		)
		self.assertEqual(rec["status"], "Disbursed")
		self.assertTrue(rec["is_direct"])
		self.assertFalse(rec["project"])
		self.assertTrue(rec["journal_entry"])

		je = frappe.db.get_value(
			"Journal Entry",
			rec["journal_entry"],
			["docstatus", "voucher_type", "petty_cash_request"],
			as_dict=True,
		)
		self.assertEqual(je.docstatus, 1)
		self.assertEqual(je.voucher_type, "Petty Cash")
		self.assertEqual(je.petty_cash_request, rec["name"])

	def test_direct_issue_reversed_is_removed(self):
		# A direct issue has no request to fall back to — reversing it removes the record.
		import json

		from buildsuite_core.api import petty_cash as pc

		rec = pc.issue_direct(
			json.dumps(
				{
					"requested_by": "Administrator",
					"amount": 500,
					"paid_from": self._cash_account(),
					"purpose": "reverse me",
				}
			)
		)
		out = pc.undisburse(rec["name"])
		self.assertTrue(out.get("deleted"))
		self.assertFalse(frappe.db.exists("Petty Cash Request", rec["name"]))

	# --- doctype guards not yet covered above ------------------------------
	def test_delete_disbursed_request_blocked(self):
		req = self._request()
		req.disburse(self._cash_account())
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Petty Cash Request", req.name, ignore_permissions=True)

	def test_disburse_rejects_invalid_paid_from(self):
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		req = self._request()

		with self.assertRaises(frappe.ValidationError):
			req.disburse(None)  # no account selected

		group_account = frappe.db.get_value("Account", {"company": self.company, "is_group": 1}, "name")
		with self.assertRaises(frappe.ValidationError):
			req.disburse(group_account)  # can't pay from a group/summary account

		expense_acct = _ensure_account(
			self.company, "UAT Non-Cash Expense", "Expense", "Expense Account", "Expenses"
		)
		with self.assertRaises(frappe.ValidationError):
			req.disburse(expense_acct)  # wrong account_type (not Bank/Cash)

	def test_cancel_disbursement_requires_disbursed_status(self):
		req = self._request()  # still Requested — never disbursed
		with self.assertRaises(frappe.ValidationError):
			req.cancel_disbursement()

	def test_disburse_rejects_zero_amount(self):
		req = self._request(amount=0)  # amount=0 passes the mandatory check (not "missing")
		with self.assertRaises(frappe.ValidationError):
			req.disburse(self._cash_account())

	def test_disburse_rejects_inactive_employee(self):
		req = self._request()
		emp = frappe.db.get_value("Employee", {"user_id": "Administrator", "status": "Active"}, "name")
		frappe.db.set_value("Employee", emp, "status", "Left")
		with self.assertRaises(frappe.ValidationError):
			req.disburse(self._cash_account())

	def test_je_submit_sync_guards(self):
		from buildsuite_core.utils.petty_cash import resolve_petty_cash_account

		holder = frappe.db.get_value("Employee", {"user_id": "Administrator", "status": "Active"}, "name")
		petty = resolve_petty_cash_account(self.company)
		bank = self._cash_account()

		# (a) already disbursed by a DIFFERENT JE — submitting a second linked JE must throw.
		req = self._request(amount=1000)
		req.disburse(bank)
		je2 = frappe.new_doc("Journal Entry")
		je2.company = self.company
		je2.posting_date = "2026-07-20"
		je2.petty_cash_request = req.name
		je2.append("accounts", {"account": petty, "debit_in_account_currency": 1000, "employee": holder})
		je2.append("accounts", {"account": bank, "credit_in_account_currency": 1000})
		je2.flags.ignore_permissions = True
		je2.insert()
		with self.assertRaises(frappe.ValidationError):
			je2.submit()

		# (b) linked to a Cancelled request — submitting the JE must throw.
		req2 = self._request(amount=500)
		frappe.db.set_value("Petty Cash Request", req2.name, "status", "Cancelled")
		je3 = frappe.new_doc("Journal Entry")
		je3.company = self.company
		je3.posting_date = "2026-07-20"
		je3.petty_cash_request = req2.name
		je3.append("accounts", {"account": petty, "debit_in_account_currency": 500, "employee": holder})
		je3.append("accounts", {"account": bank, "credit_in_account_currency": 500})
		je3.flags.ignore_permissions = True
		je3.insert()
		with self.assertRaises(frappe.ValidationError):
			je3.submit()

	def test_default_petty_cash_account_override(self):
		from buildsuite_core.utils.petty_cash import get_petty_cash_account, resolve_petty_cash_account
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		fallback = resolve_petty_cash_account(self.company)  # ensure the normal account exists
		override = _ensure_account(self.company, "UAT Petty Cash Override", "Asset", "Cash", "Current Assets")

		frappe.db.set_single_value("BuildSuite Core Settings", "default_petty_cash_account", override)
		self.assertEqual(get_petty_cash_account(self.company), override)

		frappe.db.set_single_value("BuildSuite Core Settings", "default_petty_cash_account", None)
		self.assertEqual(get_petty_cash_account(self.company), fallback)

	def test_create_account_hook_creates_petty_cash_ledger(self):
		from buildsuite_core.utils.petty_cash import PETTY_CASH_ACCOUNT_NAME, create_account

		# Already exists for the real company — must be a safe no-op (doesn't duplicate).
		before = frappe.db.count("Account", {"account_name": PETTY_CASH_ACCOUNT_NAME, "company": self.company})
		create_account(frappe._dict(name=self.company))
		after = frappe.db.count("Account", {"account_name": PETTY_CASH_ACCOUNT_NAME, "company": self.company})
		self.assertEqual(after, before)

		# No matching parent account for a company that doesn't exist -> logs an error, no throw.
		create_account(frappe._dict(name="No Such Company XYZ"))  # must not raise
		self.assertFalse(
			frappe.db.exists("Account", {"account_name": PETTY_CASH_ACCOUNT_NAME, "company": "No Such Company XYZ"})
		)

	# --- api/petty_cash.py endpoints not yet covered above ------------------
	def test_save_request_create_and_edit_guard(self):
		import json

		from buildsuite_core.api.petty_cash import save_request

		created = save_request(json.dumps({"amount": 4000, "purpose": "Site fuel", "project": self.project}))
		self.assertEqual(created["status"], "Requested")
		self.assertEqual(flt(created["amount"]), 4000)

		edited = save_request(json.dumps({"name": created["name"], "amount": 4500, "purpose": "Updated"}))
		self.assertEqual(flt(edited["amount"]), 4500)
		self.assertEqual(edited["purpose"], "Updated")

		# Once disbursed, it can no longer be edited via save_request.
		req = frappe.get_doc("Petty Cash Request", created["name"])
		req.disburse(self._cash_account())
		with self.assertRaises(frappe.ValidationError):
			save_request(json.dumps({"name": created["name"], "amount": 9999, "purpose": "nope"}))

	def test_cancel_request_via_api(self):
		from buildsuite_core.api.petty_cash import cancel_request

		req = self._request()
		out = cancel_request(req.name)
		self.assertEqual(out["status"], "Cancelled")

		# Already cancelled — a second cancel must throw.
		with self.assertRaises(frappe.ValidationError):
			cancel_request(req.name)

	def test_delete_request_via_api(self):
		from buildsuite_core.api.petty_cash import delete_request

		req = self._request()
		out = delete_request(req.name)
		self.assertTrue(out["ok"])
		self.assertFalse(frappe.db.exists("Petty Cash Request", req.name))

		req2 = self._request()
		req2.disburse(self._cash_account())
		with self.assertRaises(frappe.ValidationError):
			delete_request(req2.name)

	def test_list_cash_bank_accounts_excludes_petty_cash(self):
		from buildsuite_core.api.petty_cash import list_cash_bank_accounts
		from buildsuite_core.utils.petty_cash import resolve_petty_cash_account

		petty = resolve_petty_cash_account(self.company)
		accounts = list_cash_bank_accounts(self.company)
		names = [a["name"] for a in accounts]
		self.assertNotIn(petty, names)
		for a in accounts:
			self.assertIn(a["account_type"], ("Bank", "Cash"))

	def test_undisburse_via_api_reverts_request(self):
		from buildsuite_core.api.petty_cash import undisburse

		req = self._request()
		req.disburse(self._cash_account())
		out = undisburse(req.name)
		self.assertFalse(out.get("deleted"))
		self.assertEqual(out["status"], "Requested")
		req.reload()
		self.assertEqual(req.status, "Requested")
		self.assertFalse(req.journal_entry)

	def test_get_request_serializes_full_shape(self):
		from buildsuite_core.api.petty_cash import get_request

		req = frappe.get_doc(
			{
				"doctype": "Petty Cash Request",
				"project": self.project,
				"request_date": "2026-07-20",
				"amount": 7000,
				"purpose": "Site fuel",
			}
		).insert(ignore_permissions=True)
		req.disburse(self._cash_account())

		data = get_request(req.name)
		self.assertEqual(data["project"], self.project)
		self.assertEqual(data["project_name"], frappe.db.get_value("Project", self.project, "project_name"))
		self.assertEqual(data["status"], "Disbursed")
		self.assertTrue(data["is_mine"])  # Administrator raised it and is reading it here
		self.assertEqual(len(data["activity"]), 1)
		self.assertIn("Disbursed", data["activity"][0]["text"])

	def test_issue_direct_requires_holder_and_paid_from(self):
		import json

		from buildsuite_core.api import petty_cash as pc

		with self.assertRaises(frappe.ValidationError):
			# No requested_by (holder) given.
			pc.issue_direct(json.dumps({"amount": 1000, "paid_from": self._cash_account(), "purpose": "x"}))

		with self.assertRaises(frappe.ValidationError):
			# No paid_from account given.
			pc.issue_direct(json.dumps({"requested_by": "Administrator", "amount": 1000, "purpose": "x"}))

	def test_holder_balances_api_matches_utils(self):
		from buildsuite_core.api.petty_cash import holder_balances
		from buildsuite_core.utils.petty_cash import reconciled_holder_balances

		req = self._request(amount=4000)
		req.disburse(self._cash_account())

		self.assertEqual(holder_balances(self.company), reconciled_holder_balances(self.company))
