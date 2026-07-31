# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Invoices — the Vue front-end over ERPNext Sales Invoice: create a draft,
submit, and receive a payment into a Bank/Cash account."""

import json

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestInvoice(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _customer(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": f"Cust {self._n}",
					"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups",
					"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _deposit_account(self):
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")

	def test_create_submit_receive(self):
		from buildsuite_core.api.invoice import (
			list_invoices,
			list_receipts,
			record_receipt,
			save_invoice,
			submit_invoice,
		)

		cust = self._customer()
		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"due_date": "2026-08-20",
					"items": [{"description": "Milestone 1", "qty": 1, "rate": 100000}],
				}
			)
		)
		name = res["name"]
		si = frappe.get_doc("Sales Invoice", name)
		self.assertEqual(si.company, self.company)
		self.assertEqual(si.project, self.project)
		self.assertEqual(flt(si.grand_total), 100000)

		submit_invoice(name)

		# Partial receipt into a Bank/Cash account.
		cash = self._deposit_account()
		r = record_receipt(name, amount=40000, date="2026-07-25", mode_of_payment="Cash", deposit_to=cash)
		self.assertAlmostEqual(r["payment"]["received"], 40000, places=2)
		self.assertAlmostEqual(r["payment"]["outstanding"], 60000, places=2)
		pe = frappe.get_doc("Payment Entry", r["payment_entry"])
		self.assertEqual(pe.paid_to, cash)

		rows = [i for i in list_invoices(company=self.company, project=self.project) if i["name"] == name]
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["status"], "Partly Paid")
		self.assertAlmostEqual(rows[0]["outstanding"], 60000, places=2)
		self.assertEqual(len(list_receipts(name)), 1)

	def test_customer_advance(self):
		from buildsuite_core.api.invoice import advances_summary, record_advance

		cust = self._customer()
		cash = self._deposit_account()
		before = advances_summary(company=self.company)["total"]
		r = record_advance(cust, amount=15000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")
		pe = frappe.get_doc("Payment Entry", r["payment_entry"])
		self.assertEqual(pe.payment_type, "Receive")
		self.assertEqual(pe.party, cust)
		self.assertEqual(pe.paid_to, cash)
		self.assertAlmostEqual(flt(pe.unallocated_amount), 15000, places=2)
		self.assertAlmostEqual(advances_summary(company=self.company)["total"] - before, 15000, places=2)

	def test_taxes_and_discount(self):
		from buildsuite_core.api.invoice import get_invoice, save_invoice

		cust = self._customer()
		income_tax = frappe.db.get_value("Account", {"company": self.company, "account_type": "Tax", "is_group": 0}, "name")
		if not income_tax:
			from buildsuite_core.utils.subcontract_billing import _ensure_account

			income_tax = _ensure_account(self.company, "Output Tax", "Liability", "Tax", "Duties and Taxes")
		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "Work", "qty": 1, "rate": 100000}],
					"taxes": [{"charge_type": "On Net Total", "account_head": income_tax, "rate": 10}],
					"additional_discount_on": "Net Total",
					"additional_discount_percentage": 5,
					"terms": "Payment within 30 days.",
				}
			)
		)
		si = frappe.get_doc("Sales Invoice", res["name"])
		# 100000 − 5% = 95000 net; +10% tax = 9500 → 104500.
		self.assertAlmostEqual(flt(si.grand_total), 104500, places=2)
		self.assertEqual(len(si.taxes), 1)
		self.assertEqual(si.apply_discount_on, "Net Total")
		data = get_invoice(res["name"])
		self.assertEqual(data["additional_discount_percentage"], 5)
		self.assertEqual(data["terms"], "Payment within 30 days.")
		self.assertEqual(len(data["taxes"]), 1)

	def test_cross_company_tax_account_rejected(self):
		from buildsuite_core.api.invoice import save_invoice

		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		other_acc = frappe.db.get_value("Account", {"company": other, "is_group": 0, "root_type": "Liability"}, "name")
		if not other_acc:
			self.skipTest("no cross-company account")
		cust = self._customer()
		self.assertRaises(
			frappe.ValidationError,
			save_invoice,
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 1000}],
					"taxes": [{"charge_type": "On Net Total", "account_head": other_acc, "rate": 5}],
				}
			),
		)

	def test_draft_has_no_gl_until_submit(self):
		from buildsuite_core.api.invoice import save_invoice

		cust = self._customer()
		res = save_invoice(
			json.dumps({"customer": cust, "project": self.project, "date": "2026-07-20", "items": [{"description": "x", "qty": 2, "rate": 500}]})
		)
		si = frappe.get_doc("Sales Invoice", res["name"])
		self.assertEqual(si.docstatus, 0)
		self.assertEqual(flt(si.grand_total), 1000)
		self.assertFalse(frappe.get_all("GL Entry", filters={"voucher_no": si.name}))
