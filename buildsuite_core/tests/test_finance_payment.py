# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Payments — the unified register (api/finance_payment.py) over ERPNext
Payment Entries: classify each submitted party payment by movement type/direction, and cancel."""

import json

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestFinancePayment(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	# --- fixtures --------------------------------------------------------
	def _customer(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": f"Cust {frappe.generate_hash(length=6)}",
					"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
					or "All Customer Groups",
					"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name")
					or "All Territories",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _supplier(self):
		return (
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": f"Supp {frappe.generate_hash(length=6)}",
					"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
					or "All Supplier Groups",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _subcontractor(self):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"Sub {frappe.generate_hash(length=6)}",
				"supplier_type": "Subcontractor",
				"supplier_group": "Subcontractor",
				"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
			}
		).insert(ignore_permissions=True)

	def _cash(self):
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")

	def _submitted_invoice(self, cust, rate=50000):
		from buildsuite_core.api.invoice import save_invoice, submit_invoice

		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"due_date": "2026-08-20",
					"items": [{"description": "Milestone 1", "qty": 1, "rate": rate}],
				}
			)
		)
		submit_invoice(res["name"])
		return res["name"]

	def _submitted_bill(self, supp, rate=50000):
		from buildsuite_core.api.supplier_bill import save_bill, submit_bill

		res = save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "Cement 100 bags", "qty": 1, "rate": rate}],
				}
			)
		)
		submit_bill(res["name"])
		return res["name"]

	def _submitted_subcontractor_bill(self, sub, amount=100000, retention=10):
		bill = frappe.get_doc(
			{
				"doctype": "Subcontractor Bill",
				"is_direct": 1,
				"subcontractor": sub.name,
				"project": self.project,
				"company": self.company,
				"date": "2026-07-20",
				"retention_percent": retention,
				"lines": [{"scope": "Site clearance", "this_period_amount": amount}],
			}
		)
		bill.insert(ignore_permissions=True)
		bill.submit()
		return bill.reload()

	# --- classification ----------------------------------------------------
	def test_list_payments_classifies_invoice_receipt(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.invoice import record_receipt

		cust = self._customer()
		cash = self._cash()
		name = self._submitted_invoice(cust, rate=50000)
		r = record_receipt(name, amount=50000, date="2026-07-25", mode_of_payment="Cash", deposit_to=cash)

		rows = {p["name"]: p for p in list_payments(company=self.company)}
		row = rows[r["payment_entry"]]
		self.assertEqual(row["type"], "Invoice receipt")
		self.assertEqual(row["dir"], "in")
		self.assertAlmostEqual(row["amount"], 50000, places=2)
		self.assertEqual(row["ref"], name)

	def test_list_payments_classifies_customer_advance(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.invoice import record_advance

		cust = self._customer()
		cash = self._cash()
		r = record_advance(cust, amount=15000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")

		rows = {p["name"]: p for p in list_payments(company=self.company)}
		row = rows[r["payment_entry"]]
		self.assertEqual(row["type"], "Customer advance")
		self.assertEqual(row["dir"], "in")

	def test_list_payments_classifies_bill_payment(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.supplier_bill import record_payment

		supp = self._supplier()
		cash = self._cash()
		name = self._submitted_bill(supp, rate=30000)
		r = record_payment(name, amount=30000, date="2026-07-25", mode_of_payment="Cash", pay_from=cash)

		rows = {p["name"]: p for p in list_payments(company=self.company)}
		row = rows[r["payment_entry"]]
		self.assertEqual(row["type"], "Bill payment")
		self.assertEqual(row["dir"], "out")
		self.assertEqual(row["ref"], name)

	def test_list_payments_classifies_subcontractor_payment(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.subcontractor_bill import record_payment

		sub = self._subcontractor()
		cash = self._cash()
		bill = self._submitted_subcontractor_bill(sub, amount=100000, retention=10)
		res = record_payment(bill.name, amount=50000, date="2026-07-21", mode_of_payment="Cash", paid_from=cash)

		rows = {p["name"]: p for p in list_payments(company=self.company)}
		row = rows[res["payment_entry"]]
		self.assertEqual(row["type"], "Subcontractor payment")
		self.assertEqual(row["dir"], "out")
		# The ref points at the Subcontractor Bill, not the underlying Purchase Invoice.
		self.assertEqual(row["ref"], bill.name)

	def test_list_payments_classifies_supplier_advance(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.supplier_bill import record_advance

		supp = self._supplier()
		cash = self._cash()
		r = record_advance(supp, amount=20000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")

		rows = {p["name"]: p for p in list_payments(company=self.company)}
		row = rows[r["payment_entry"]]
		self.assertEqual(row["type"], "Supplier advance")
		self.assertEqual(row["dir"], "out")

	def test_list_payments_classifies_subcontractor_advance(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.supplier_bill import record_advance

		sub = self._subcontractor()
		cash = self._cash()
		r = record_advance(sub.name, amount=20000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")

		rows = {p["name"]: p for p in list_payments(company=self.company)}
		row = rows[r["payment_entry"]]
		self.assertEqual(row["type"], "Subcontractor advance")
		self.assertEqual(row["dir"], "out")

	# --- listing scope -------------------------------------------------------
	def test_list_payments_excludes_draft_and_cancelled(self):
		from buildsuite_core.api.finance_payment import cancel_payment, list_payments
		from buildsuite_core.api.invoice import record_receipt

		cust = self._customer()
		cash = self._cash()

		# A draft PE (never submitted) never appears.
		name = self._submitted_invoice(cust, rate=10000)
		draft_pe = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Receive",
				"company": self.company,
				"party_type": "Customer",
				"party": cust,
				"paid_from": frappe.db.get_value("Company", self.company, "default_receivable_account"),
				"paid_to": cash,
				"paid_amount": 1000,
				"received_amount": 1000,
			}
		).insert(ignore_permissions=True)

		names_before = {p["name"] for p in list_payments(company=self.company)}
		self.assertNotIn(draft_pe.name, names_before)

		# A submitted PE that's then cancelled also drops out.
		r = record_receipt(name, amount=10000, date="2026-07-25", mode_of_payment="Cash", deposit_to=cash)
		self.assertIn(r["payment_entry"], {p["name"] for p in list_payments(company=self.company)})
		cancel_payment(r["payment_entry"])
		self.assertNotIn(r["payment_entry"], {p["name"] for p in list_payments(company=self.company)})

	def test_list_payments_newest_first(self):
		from buildsuite_core.api.finance_payment import list_payments
		from buildsuite_core.api.invoice import record_advance

		cust = self._customer()
		cash = self._cash()
		older = record_advance(cust, amount=1000, date="2026-07-10", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		newer = record_advance(cust, amount=1000, date="2026-07-30", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]

		names = [p["name"] for p in list_payments(company=self.company)]
		self.assertLess(names.index(newer), names.index(older))

	# --- cancel ---------------------------------------------------------------
	def test_cancel_payment_reverses_invoice_outstanding(self):
		from buildsuite_core.api.finance_payment import cancel_payment, list_payments
		from buildsuite_core.api.invoice import record_receipt

		cust = self._customer()
		cash = self._cash()
		name = self._submitted_invoice(cust, rate=25000)
		r = record_receipt(name, amount=25000, date="2026-07-25", mode_of_payment="Cash", deposit_to=cash)
		self.assertAlmostEqual(flt(frappe.get_doc("Sales Invoice", name).outstanding_amount), 0, places=2)

		out = cancel_payment(r["payment_entry"])
		self.assertTrue(out["cancelled"])
		self.assertAlmostEqual(
			flt(frappe.get_doc("Sales Invoice", name).outstanding_amount), 25000, places=2
		)
		self.assertNotIn(r["payment_entry"], {p["name"] for p in list_payments(company=self.company)})
