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
					{
						"description": "Tiling work",
						"work_order_line": line,
						"quantity": qty,
						"is_deduction": 0,
					}
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

	def test_direct_bill_requires_a_project(self):
		# The project anchors the accounting company, so a direct bill must have one.
		from frappe.exceptions import MandatoryError

		bill = frappe.get_doc(
			{
				"doctype": "Subcontractor Bill",
				"is_direct": 1,
				"subcontractor": self._subcontractor().name,
				"date": "2026-07-22",
				"retention_percent": 0,
				"lines": [{"scope": "One-off charge", "this_period_amount": 5000}],
			}
		)
		self.assertRaises(MandatoryError, bill.insert, ignore_permissions=True)

	def test_make_payment_entry_creates_draft_against_pi(self):
		from buildsuite_core.api.subcontractor_bill import make_payment_entry

		bill = self._direct_bill(self._subcontractor(), amount=100000, retention=10)
		bill.submit()
		bill.reload()
		res = make_payment_entry(bill.name)
		pe = frappe.get_doc("Payment Entry", res["payment_entry"])
		self.assertEqual(pe.docstatus, 0)  # draft — user reviews + submits in Desk
		self.assertTrue(any(r.reference_name == bill.purchase_invoice for r in pe.references))

	def test_tax_account_company_mismatch_rejected(self):
		# A tax-row account from another company must be rejected up front (the PI would post
		# to the wrong company's GL). Consistency validated on the bill, not deep in the PI.
		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		other_acct = frappe.db.get_value(
			"Account", {"company": other, "is_group": 0, "root_type": "Liability"}, "name"
		)
		if not other_acct:
			self.skipTest("no cross-company account available")
		bill = self._direct_bill(self._subcontractor(), amount=1000, retention=0)
		bill.append("taxes", {"charge_type": "On Net Total", "account_head": other_acct, "rate": 5})
		self.assertRaises(frappe.ValidationError, bill.save)

	def test_work_order_company_anchored_to_project(self):
		# A WO always takes its project's company, even if a different one is supplied — so the
		# inconsistency that broke PI posting can't be created in the first place.
		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		wo = frappe.get_doc(
			{
				"doctype": "Subcontractor Work Order",
				"subcontractor": self._subcontractor().name,
				"project": self.project,
				"company": other,  # deliberately wrong
				"date": "2026-07-01",
				"retention_percent": 5,
				"lines": [{"scope": "X", "uom": "Nos", "qty": 1, "rate": 1}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(wo.company, frappe.db.get_value("Project", self.project, "company"))

	def test_bill_company_follows_project_not_work_order(self):
		# A WO whose company has drifted from its project's must not leak that company onto
		# the bill (the PI validates the project against the company). Anchor to the project.
		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company to simulate the drift")
		sub = self._subcontractor()
		wo = self._work_order(sub, qty=100, rate=85)
		frappe.db.set_value("Subcontractor Work Order", wo.name, "company", other)  # drift
		self._certified_mb(wo, qty=40)
		bill = frappe.get_doc({"doctype": "Subcontractor Bill", "work_order": wo.name, "date": "2026-07-20"})
		bill.fetch_lines()
		bill.insert(ignore_permissions=True)
		self.assertEqual(bill.company, frappe.db.get_value("Project", self.project, "company"))

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

		bill = frappe.get_doc({"doctype": "Subcontractor Bill", "work_order": wo.name, "date": "2026-07-20"})
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

	def test_advance_adjusted_against_bill_pi(self):
		"""A subcontractor advance links to the bill's generated PI, settles the payable, is
		excluded from cash payments, and unlinks cleanly."""
		from buildsuite_core.api import subcontractor_bill as SC
		from buildsuite_core.api.supplier_bill import record_advance
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		sub = self._subcontractor()
		cash = _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")
		bill = self._direct_bill(sub, amount=100000, retention=10)  # net payable 90000
		bill.submit()
		bill.reload()

		pe = record_advance(sub.name, amount=40000, date="2026-07-21", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		self.assertEqual(len([a for a in SC.available_advances(bill.name) if a["payment_entry"] == pe]), 1)

		SC.link_advance(bill.name, pe, 30000)
		data = SC.get_bill(bill.name)
		self.assertEqual(len(data["advances"]), 1)
		self.assertAlmostEqual(data["advance_adjusted"], 30000, places=2)
		self.assertAlmostEqual(data["payment"]["paid"], 0, places=2)  # advance is not a cash payment
		self.assertEqual(len(SC.list_payments(bill.name)), 0)
		self.assertAlmostEqual(
			flt(frappe.get_doc("Purchase Invoice", bill.purchase_invoice).outstanding_amount), 60000, places=2
		)

		SC.unlink_advance(bill.name, pe)
		self.assertAlmostEqual(
			flt(frappe.get_doc("Purchase Invoice", bill.purchase_invoice).outstanding_amount), 90000, places=2
		)
		self.assertAlmostEqual(
			flt(frappe.db.get_value("Payment Entry", pe, "unallocated_amount")), 40000, places=2
		)
		self.assertEqual(len(SC.get_bill(bill.name)["advances"]), 0)

	def test_advance_linking_needs_a_submitted_bill(self):
		"""A draft bill has no Purchase Invoice, so it offers no advances and rejects a link."""
		from buildsuite_core.api import subcontractor_bill as SC
		from buildsuite_core.api.supplier_bill import record_advance
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		sub = self._subcontractor()
		cash = _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")
		bill = self._direct_bill(sub, amount=50000, retention=0)  # draft — no PI yet
		pe = record_advance(sub.name, amount=10000, date="2026-07-21", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		self.assertEqual(SC.available_advances(bill.name), [])
		self.assertRaises(frappe.ValidationError, SC.link_advance, bill.name, pe, 5000)

	def test_record_payment_uses_paid_from_account(self):
		from buildsuite_core.api.subcontractor_bill import list_pay_accounts, record_payment
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		cash = _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")
		# list_pay_accounts returns only Bank/Cash accounts for the company.
		accounts = list_pay_accounts(self.company)
		self.assertIn(cash, [a["name"] for a in accounts])
		self.assertTrue(all(a["account_type"] in ("Bank", "Cash") for a in accounts))

		bill = self._direct_bill(self._subcontractor(), amount=100000, retention=10)
		bill.submit()
		bill.reload()
		res = record_payment(
			bill.name, amount=25000, date="2026-07-21", mode_of_payment="Cash", paid_from=cash
		)
		pe = frappe.get_doc("Payment Entry", res["payment_entry"])
		self.assertEqual(pe.paid_from, cash)
