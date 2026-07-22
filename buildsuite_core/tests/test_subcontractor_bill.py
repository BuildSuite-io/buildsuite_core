# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Subcontractor Bill → Purchase Invoice generation, both modes, plus payment/cancel.

The bill is the front-end instrument; the PI it generates on submit does the accounting
(payable, retention, taxes) via ERPNext's framework. Taxes are country-agnostic — nothing
here is GST-specific."""

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestSubcontractorBill(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		# The interactively-configured default company (consistent CoA currency), not the
		# arbitrary first company base picks — this site has several part-configured ones.
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	# --- builders --------------------------------------------------------
	def _subcontractor(self):
		"""A subcontractor is a native Supplier tagged supplier_type='Subcontractor'."""
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"Sub {self._n}",
				"supplier_type": "Subcontractor",
				"supplier_group": "Subcontractor",
				"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
			}
		).insert(ignore_permissions=True)

	def _work_order(self, sub, qty=100, rate=85):
		wo = frappe.get_doc(
			{
				"doctype": "Subcontractor Work Order",
				"subcontractor": sub.name,
				"project": self.project,
				"company": self.company,
				"date": "2026-07-01",
				"retention_percent": 5,
				"lines": [{"scope": "Tiling", "uom": "Nos", "qty": qty, "rate": rate}],
			}
		).insert(ignore_permissions=True)
		wo.db_set("status", "Awarded")
		return wo.reload()

	def _certified_mb(self, wo, qty):
		line = wo.lines[0].name
		mb = frappe.get_doc(
			{
				"doctype": "Measurement Book",
				"work_order": wo.name,
				"project": self.project,
				"date": "2026-07-05",
				"entries": [
					{"description": "Tiling work", "work_order_line": line, "quantity": qty, "is_deduction": 0}
				],
			}
		).insert(ignore_permissions=True)
		mb.db_set("status", "Certified")
		return mb

	def _direct_bill(self, sub, amount=100000, retention=10, **kw):
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
				**kw,
			}
		)
		bill.insert(ignore_permissions=True)
		return bill

	# --- tests -----------------------------------------------------------
	def test_direct_bill_waterfall(self):
		bill = self._direct_bill(self._subcontractor(), amount=100000, retention=10)
		self.assertEqual(flt(bill.gross), 100000)
		self.assertEqual(flt(bill.taxable_value), 100000)
		self.assertEqual(flt(bill.retention_amount), 10000)
		self.assertEqual(flt(bill.net_payable), 90000)

	def test_submit_generates_pi_against_the_supplier(self):
		sub = self._subcontractor()  # the subcontractor IS a Supplier
		bill = self._direct_bill(sub, amount=100000, retention=10)
		bill.submit()
		bill.reload()

		self.assertTrue(bill.purchase_invoice)
		self.assertEqual(bill.status, "Submitted")

		pi = frappe.get_doc("Purchase Invoice", bill.purchase_invoice)
		# The PI posts directly against the subcontractor Supplier — no shadow supplier.
		self.assertEqual(pi.supplier, sub.name)
		self.assertEqual(pi.subcontractor_bill, bill.name)
		# Expense recognised at FULL value (100k); retention only reduces the payable.
		self.assertEqual(flt(pi.total), 100000)
		deduct = [t for t in pi.taxes if t.add_deduct_tax == "Deduct"]
		self.assertTrue(any("Retention" in (t.description or "") for t in deduct))
		self.assertAlmostEqual(flt(pi.grand_total), 90000, places=2)

	def test_expense_account_flows_to_pi(self):
		from buildsuite_core.utils.subcontract_billing import resolve_accounts

		acct = resolve_accounts(self.company)["expense"]
		bill = self._direct_bill(self._subcontractor(), amount=50000, retention=0, expense_account=acct)
		bill.submit()
		bill.reload()
		pi = frappe.get_doc("Purchase Invoice", bill.purchase_invoice)
		self.assertTrue(all(item.expense_account == acct for item in pi.items))

	def test_submit_via_api_with_db_loaded_date(self):
		# Regression: the API submit path reloads the bill from the DB, so `date` is a
		# datetime.date — the PI's get_due_date() is strictly typed str|None and must not trip.
		from buildsuite_core.api.subcontractor_bill import submit_bill

		bill = self._direct_bill(self._subcontractor(), amount=100000, retention=10)
		res = submit_bill(bill.name)
		self.assertTrue(res["purchase_invoice"])

	def test_pi_generation_is_idempotent(self):
		bill = self._direct_bill(self._subcontractor())
		bill.submit()
		bill.reload()
		from buildsuite_core.utils.subcontract_billing import generate_purchase_invoice

		again = generate_purchase_invoice(bill)
		self.assertEqual(again, bill.purchase_invoice)

	def test_cancel_cancels_pi(self):
		bill = self._direct_bill(self._subcontractor())
		bill.submit()
		bill.reload()
		pi = bill.purchase_invoice
		bill.cancel()
		self.assertEqual(frappe.db.get_value("Purchase Invoice", pi, "docstatus"), 2)

	def test_wo_bill_derives_from_measurement_book(self):
		sub = self._subcontractor()
		wo = self._work_order(sub, qty=100, rate=85)
		self._certified_mb(wo, qty=40)

		bill = frappe.get_doc(
			{"doctype": "Subcontractor Bill", "work_order": wo.name, "date": "2026-07-20"}
		)
		bill.fetch_lines()
		bill.insert(ignore_permissions=True)
		# 40 measured × 85 = 3400 gross; retention 5% = 170.
		self.assertEqual(flt(bill.gross), 3400)
		self.assertEqual(flt(bill.retention_amount), 170)
		bill.submit()
		self.assertTrue(bill.reload().purchase_invoice)

	def test_previously_billed_rolls_forward(self):
		sub = self._subcontractor()
		wo = self._work_order(sub, qty=100, rate=85)
		self._certified_mb(wo, qty=40)
		b1 = frappe.get_doc({"doctype": "Subcontractor Bill", "work_order": wo.name, "date": "2026-07-20"})
		b1.fetch_lines()
		b1.insert(ignore_permissions=True)
		b1.submit()

		# More measured (cumulative 70); RA-2 should bill only the fresh 30.
		self._certified_mb(wo, qty=30)
		b2 = frappe.get_doc({"doctype": "Subcontractor Bill", "work_order": wo.name, "date": "2026-07-25"})
		b2.fetch_lines()
		self.assertEqual(flt(b2.lines[0].previous_qty), 40)
		self.assertEqual(flt(b2.lines[0].this_period_qty), 30)

	def test_record_payment_reduces_outstanding(self):
		from buildsuite_core.api.subcontractor_bill import record_payment

		bill = self._direct_bill(self._subcontractor(), amount=100000, retention=10)
		bill.submit()
		bill.reload()
		res = record_payment(bill.name, amount=50000, date="2026-07-21", mode_of_payment="Cash")
		self.assertAlmostEqual(res["payment"]["paid"], 50000, places=2)
		self.assertAlmostEqual(res["payment"]["outstanding"], 40000, places=2)
