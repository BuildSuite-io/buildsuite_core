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
					"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
					or "All Customer Groups",
					"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name")
					or "All Territories",
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
		income_tax = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Tax", "is_group": 0}, "name"
		)
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
		other_acc = frappe.db.get_value(
			"Account", {"company": other, "is_group": 0, "root_type": "Liability"}, "name"
		)
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

	def test_seed_invoice_terms_and_plain_text(self):
		from buildsuite_core.api.invoice import _html_to_text
		from buildsuite_core.install import seed_invoice_terms

		seed_invoice_terms()  # idempotent
		self.assertTrue(frappe.db.exists("Terms and Conditions", "Standard Sales Invoice"))
		# HTML terms render as friendly plain text (block tags → newlines, tags stripped).
		self.assertEqual(_html_to_text("<p>A</p><p>B</p>"), "A\nB")
		self.assertEqual(_html_to_text("1. Plain\n2. Text"), "1. Plain\n2. Text")

	def _draft_invoice(self, cust, rate=50000):
		from buildsuite_core.api.invoice import save_invoice

		return save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"due_date": "2026-08-20",
					"items": [{"description": "Work", "qty": 1, "rate": rate}],
				}
			)
		)["name"]

	def test_link_advance_on_draft(self):
		"""A customer advance adjusted against a DRAFT invoice lands in the native `advances`
		table, reduces outstanding, and unlinks cleanly."""
		from buildsuite_core.api.invoice import (
			available_advances,
			get_invoice,
			link_advance,
			record_advance,
			unlink_advance,
		)

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=30000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=50000)

		avail = [a for a in available_advances(name) if a["payment_entry"] == pe]
		self.assertEqual(len(avail), 1)
		self.assertAlmostEqual(avail[0]["unallocated"], 30000, places=2)

		link_advance(name, pe, 20000)
		data = get_invoice(name)
		self.assertEqual(len(data["advances"]), 1)
		self.assertEqual(data["advances"][0]["payment_entry"], pe)
		self.assertAlmostEqual(data["advance_adjusted"], 20000, places=2)
		# The advance settles part of the receivable even before submit.
		si = frappe.get_doc("Sales Invoice", name)
		self.assertAlmostEqual(flt(si.outstanding_amount), 30000, places=2)

		unlink_advance(name, pe)
		self.assertEqual(len(get_invoice(name)["advances"]), 0)
		self.assertAlmostEqual(
			flt(frappe.db.get_value("Payment Entry", pe, "unallocated_amount")), 30000, places=2
		)

	def test_draft_advance_caps_and_submits(self):
		"""An advance adjusted on a draft drops out of 'available' once fully used, cannot be
		re-linked past its balance, and the draft then submits cleanly (regression: a re-linked
		advance used to pile up allocated_amount beyond the Payment Entry and block submit)."""
		from buildsuite_core.api.invoice import (
			available_advances,
			get_invoice,
			link_advance,
			list_receipts,
			record_advance,
			submit_invoice,
		)

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=40000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=200000)

		link_advance(name, pe, 40000)
		# Fully adjusted → no longer offered as available, and a re-link is rejected.
		self.assertEqual([a for a in available_advances(name) if a["payment_entry"] == pe], [])
		self.assertRaises(frappe.ValidationError, link_advance, name, pe, 10000)

		si = frappe.get_doc("Sales Invoice", name)
		self.assertAlmostEqual(flt(si.advances[0].allocated_amount), 40000, places=2)
		self.assertLessEqual(flt(si.advances[0].allocated_amount), flt(si.advances[0].advance_amount) + 0.01)
		submit_invoice(name)  # must not raise "Allocated amount cannot be greater than unadjusted amount"
		si.reload()
		self.assertEqual(si.docstatus, 1)
		self.assertAlmostEqual(flt(si.outstanding_amount), 160000, places=2)
		# Post-submit the advance is RETAINED as an advance (not reclassified as a cash receipt),
		# even though it is fully consumed — so the waterfall keeps showing "Advance adjusted".
		data = get_invoice(name)
		self.assertAlmostEqual(data["advance_adjusted"], 40000, places=2)
		self.assertEqual(len(data["advances"]), 1)
		self.assertAlmostEqual(data["payment"]["received"], 0, places=2)
		self.assertEqual(len(list_receipts(name)), 0)

	def test_link_advance_on_submitted(self):
		"""A partial advance adjusted against a SUBMITTED invoice reconciles natively (PE
		reference), reduces outstanding, is excluded from receipts, and unlinks (unreconcile)."""
		from buildsuite_core.api.invoice import (
			get_invoice,
			link_advance,
			list_receipts,
			record_advance,
			submit_invoice,
			unlink_advance,
		)

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=100000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=60000)
		submit_invoice(name)

		link_advance(name, pe, 40000)
		si = frappe.get_doc("Sales Invoice", name)
		self.assertAlmostEqual(flt(si.outstanding_amount), 20000, places=2)
		self.assertAlmostEqual(
			flt(frappe.db.get_value("Payment Entry", pe, "unallocated_amount")), 60000, places=2
		)

		data = get_invoice(name)
		self.assertEqual(len(data["advances"]), 1)
		self.assertAlmostEqual(data["advance_adjusted"], 40000, places=2)
		self.assertAlmostEqual(data["payment"]["received"], 0, places=2)
		# The reconciled advance is not counted as a cash receipt.
		self.assertEqual(len(list_receipts(name)), 0)

		unlink_advance(name, pe)
		si.reload()
		self.assertAlmostEqual(flt(si.outstanding_amount), 60000, places=2)
		self.assertAlmostEqual(
			flt(frappe.db.get_value("Payment Entry", pe, "unallocated_amount")), 100000, places=2
		)
		self.assertEqual(len(get_invoice(name)["advances"]), 0)

	def test_same_advance_reconciled_in_multiple_steps(self):
		"""Adjusting the SAME advance against a submitted invoice several times sums into ONE
		Advance Payments line (regression: only the first reconciliation used to count; the rest
		leaked into 'Received')."""
		from buildsuite_core.api.invoice import (
			get_invoice,
			link_advance,
			list_receipts,
			record_advance,
			submit_invoice,
		)

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=70000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=100000)
		submit_invoice(name)

		link_advance(name, pe, 10000)
		link_advance(name, pe, 15000)
		link_advance(name, pe, 6000)  # same advance, three steps → 31000 total

		data = get_invoice(name)
		adv_rows = [a for a in data["advances"] if a["payment_entry"] == pe]
		self.assertEqual(len(adv_rows), 1)
		self.assertAlmostEqual(adv_rows[0]["allocated"], 31000, places=2)
		self.assertAlmostEqual(data["advance_adjusted"], 31000, places=2)
		self.assertAlmostEqual(data["payment"]["received"], 0, places=2)
		self.assertEqual(len(list_receipts(name)), 0)
		self.assertAlmostEqual(
			flt(frappe.db.get_value("Payment Entry", pe, "unallocated_amount")), 39000, places=2
		)

	def test_draft_has_no_gl_until_submit(self):
		from buildsuite_core.api.invoice import save_invoice

		cust = self._customer()
		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 2, "rate": 500}],
				}
			)
		)
		si = frappe.get_doc("Sales Invoice", res["name"])
		self.assertEqual(si.docstatus, 0)
		self.assertEqual(flt(si.grand_total), 1000)
		self.assertFalse(frappe.get_all("GL Entry", filters={"voucher_no": si.name}))
