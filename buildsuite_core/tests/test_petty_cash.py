# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Petty Cash Request → Journal Entry on disburse (the live part of Project Finance)."""

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPettyCash(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _cash_account(self):
		acc = frappe.db.get_value(
			"Account", {"company": self.company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
		)
		if acc:
			return acc
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")

	def _request(self, amount=15000, purpose="Diesel + site consumables"):
		return frappe.get_doc(
			{
				"doctype": "Petty Cash Request",
				"project": self.project,
				"request_date": "2026-07-20",
				"amount": amount,
				"purpose": purpose,
			}
		).insert(ignore_permissions=True)

	def test_company_anchored_to_project(self):
		req = self._request()
		self.assertEqual(req.company, frappe.db.get_value("Project", self.project, "company"))

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
		# Dr Petty Cash 15000 / Cr bank 15000, both carrying the project dimension.
		self.assertEqual(flt(debit[0].debit_in_account_currency), 15000)
		self.assertEqual(credit[0].account, bank)
		self.assertEqual(flt(credit[0].credit_in_account_currency), 15000)
		self.assertTrue(all(a.project == self.project for a in je.accounts))

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
