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
