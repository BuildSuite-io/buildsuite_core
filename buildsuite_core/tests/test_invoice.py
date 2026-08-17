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

	# --- A: cancel / delete / receivables summary ---------------------------
	def test_cancel_invoice_reflects_in_summary_and_blocks_advances(self):
		from buildsuite_core.api.invoice import (
			cancel_invoice,
			get_invoice,
			link_advance,
			record_advance,
			submit_invoice,
			unlink_advance,
		)

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=10000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=50000)
		submit_invoice(name)
		cancel_invoice(name)

		si = frappe.get_doc("Sales Invoice", name)
		self.assertEqual(si.docstatus, 2)
		data = get_invoice(name)
		self.assertEqual(data["payment"]["status"], "Cancelled")

		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 1000)
		with self.assertRaises(frappe.ValidationError):
			unlink_advance(name, pe)

	def test_delete_invoice_requires_draft(self):
		from buildsuite_core.api.invoice import delete_invoice, submit_invoice

		cust = self._customer()
		name = self._draft_invoice(cust)
		delete_invoice(name)
		self.assertFalse(frappe.db.exists("Sales Invoice", name))

		name2 = self._draft_invoice(cust)
		submit_invoice(name2)
		with self.assertRaises(frappe.ValidationError):
			delete_invoice(name2)

	def test_receivables_summary_aggregates_outstanding(self):
		from buildsuite_core.api.invoice import receivables_summary, record_advance, submit_invoice

		cust = self._customer()
		cash = self._deposit_account()
		before = receivables_summary(company=self.company)
		name = self._draft_invoice(cust, rate=30000)
		submit_invoice(name)
		record_advance(cust, amount=5000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")

		after = receivables_summary(company=self.company)
		self.assertAlmostEqual(after["outstanding"] - before["outstanding"], 30000, places=2)
		self.assertAlmostEqual(after["advances"] - before["advances"], 5000, places=2)

	# --- B: save_invoice — untested branches --------------------------------
	def test_save_invoice_edit_existing_draft_replaces_lines(self):
		from buildsuite_core.api.invoice import save_invoice

		cust = self._customer()
		name = self._draft_invoice(cust, rate=10000)
		save_invoice(
			json.dumps(
				{
					"name": name,
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "New Line", "qty": 2, "rate": 5000}],
				}
			)
		)
		si = frappe.get_doc("Sales Invoice", name)
		self.assertEqual(len(si.items), 1)
		self.assertEqual(si.items[0].description, "New Line")
		self.assertAlmostEqual(flt(si.grand_total), 10000, places=2)

	def test_save_invoice_requires_customer_and_at_least_one_line(self):
		from buildsuite_core.api.invoice import save_invoice

		cust = self._customer()
		with self.assertRaises(frappe.ValidationError):
			save_invoice(
				json.dumps(
					{
						"project": self.project,
						"date": "2026-07-20",
						"items": [{"description": "x", "qty": 1, "rate": 100}],
					}
				)
			)
		with self.assertRaises(frappe.ValidationError):
			save_invoice(
				json.dumps({"customer": cust, "project": self.project, "date": "2026-07-20", "items": []})
			)

	def test_save_invoice_edit_only_while_draft(self):
		from buildsuite_core.api.invoice import save_invoice, submit_invoice

		cust = self._customer()
		name = self._draft_invoice(cust)
		submit_invoice(name)
		with self.assertRaises(frappe.ValidationError):
			save_invoice(
				json.dumps(
					{
						"name": name,
						"customer": cust,
						"project": self.project,
						"date": "2026-07-20",
						"items": [{"description": "x", "qty": 1, "rate": 999}],
					}
				)
			)

	def test_save_invoice_due_date_defaults_to_posting_date(self):
		from buildsuite_core.api.invoice import save_invoice

		cust = self._customer()
		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 1000}],
				}
			)
		)
		si = frappe.get_doc("Sales Invoice", res["name"])
		self.assertEqual(str(si.due_date), "2026-07-20")

	def test_save_invoice_flat_and_grand_total_discount_modes(self):
		from buildsuite_core.api.invoice import save_invoice

		cust = self._customer()
		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 100000}],
					"discount_amount": 10000,
				}
			)
		)
		si = frappe.get_doc("Sales Invoice", res["name"])
		self.assertAlmostEqual(flt(si.grand_total), 90000, places=2)

		res2 = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 100000}],
					"additional_discount_on": "Grand Total",
					"additional_discount_percentage": 10,
				}
			)
		)
		si2 = frappe.get_doc("Sales Invoice", res2["name"])
		self.assertEqual(si2.apply_discount_on, "Grand Total")
		self.assertAlmostEqual(flt(si2.grand_total), 90000, places=2)

	def test_save_invoice_tax_template_expands_rows(self):
		from buildsuite_core.api.invoice import save_invoice

		income_tax = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Tax", "is_group": 0}, "name"
		)
		if not income_tax:
			from buildsuite_core.utils.subcontract_billing import _ensure_account

			income_tax = _ensure_account(self.company, "Output Tax", "Liability", "Tax", "Duties and Taxes")

		template = frappe.get_doc(
			{
				"doctype": "Sales Taxes and Charges Template",
				"title": f"UAT Template {self._n}",
				"company": self.company,
				"taxes": [
					{"charge_type": "On Net Total", "account_head": income_tax, "description": "Tax", "rate": 8}
				],
			}
		).insert(ignore_permissions=True)

		cust = self._customer()
		res = save_invoice(
			json.dumps(
				{
					"customer": cust,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 100000}],
					"taxes_and_charges": template.name,
				}
			)
		)
		si = frappe.get_doc("Sales Invoice", res["name"])
		self.assertEqual(len(si.taxes), 1)
		self.assertEqual(si.taxes[0].account_head, income_tax)
		self.assertAlmostEqual(flt(si.grand_total), 108000, places=2)

	# --- C: record_receipt gaps ---------------------------------------------
	def test_record_receipt_requires_submitted_invoice(self):
		from buildsuite_core.api.invoice import record_receipt

		cust = self._customer()
		name = self._draft_invoice(cust)
		with self.assertRaises(frappe.ValidationError):
			record_receipt(name, amount=1000, deposit_to=self._deposit_account())

	def test_record_receipt_rejects_cross_company_deposit_account(self):
		from buildsuite_core.api.invoice import record_receipt, submit_invoice

		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		other_acct = frappe.db.get_value(
			"Account", {"company": other, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
		)
		if not other_acct:
			self.skipTest("no cross-company bank/cash account")

		cust = self._customer()
		name = self._draft_invoice(cust, rate=10000)
		submit_invoice(name)
		with self.assertRaises(frappe.ValidationError):
			record_receipt(name, amount=1000, deposit_to=other_acct)

	def test_record_receipt_default_amount_uses_full_outstanding(self):
		from buildsuite_core.api.invoice import record_receipt, submit_invoice

		cust = self._customer()
		name = self._draft_invoice(cust, rate=25000)
		submit_invoice(name)
		r = record_receipt(name, deposit_to=self._deposit_account())  # no amount -> full outstanding
		self.assertAlmostEqual(r["payment"]["received"], 25000, places=2)
		self.assertAlmostEqual(r["payment"]["outstanding"], 0, places=2)

	def test_record_receipt_marks_paid_when_fully_settled(self):
		from buildsuite_core.api.invoice import record_receipt, submit_invoice

		cust = self._customer()
		name = self._draft_invoice(cust, rate=15000)
		submit_invoice(name)
		r = record_receipt(name, amount=15000, deposit_to=self._deposit_account(), mode_of_payment="Cash")
		self.assertEqual(r["payment"]["status"], "Paid")

	# --- D: record_advance guards --------------------------------------------
	def test_record_advance_validation_guards(self):
		from buildsuite_core.api.invoice import record_advance

		cust = self._customer()
		cash = self._deposit_account()
		with self.assertRaises(frappe.ValidationError):
			record_advance(cust, amount=0, deposit_to=cash)
		with self.assertRaises(frappe.ValidationError):
			record_advance(cust, amount=1000, deposit_to=None)

		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if other:
			other_acct = frappe.db.get_value(
				"Account", {"company": other, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
			)
			if other_acct:
				with self.assertRaises(frappe.ValidationError):
					record_advance(cust, amount=1000, deposit_to=other_acct)

	# --- E: link_advance / unlink_advance ------------------------------------
	def test_link_advance_rejects_non_advance_or_wrong_customer(self):
		from buildsuite_core.api.invoice import link_advance, record_advance

		cust = self._customer()
		other_cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(
			other_cust, amount=10000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash"
		)["payment_entry"]
		name = self._draft_invoice(cust, rate=5000)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 1000)  # PE belongs to a different customer

	def test_link_advance_rejects_over_allocation_beyond_pe_room(self):
		from buildsuite_core.api.invoice import link_advance, record_advance

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=5000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=50000)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 10000)  # more than the PE's 5000 unallocated

	def test_link_advance_invoice_room_is_the_binding_cap(self):
		from buildsuite_core.api.invoice import link_advance, record_advance

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=100000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=20000)  # the invoice total is the binding constraint here
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 30000)  # the PE has plenty, but the invoice can only take 20000
		link_advance(name, pe, 20000)  # exactly the invoice total succeeds
		si = frappe.get_doc("Sales Invoice", name)
		self.assertAlmostEqual(flt(si.outstanding_amount), 0, places=2)

	def test_link_advance_partial_relink_room_message(self):
		from buildsuite_core.api.invoice import link_advance, record_advance

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=100000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=50000)
		link_advance(name, pe, 30000)  # room left afterward = 20000 (invoice-side)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 25000)  # exceeds the remaining 20000 room (but room > 0)
		link_advance(name, pe, 20000)  # exactly the remaining room succeeds

	def test_link_advance_blocked_on_settled_or_cancelled_invoice(self):
		from buildsuite_core.api.invoice import (
			cancel_invoice,
			link_advance,
			record_advance,
			submit_invoice,
		)

		cust = self._customer()
		cash = self._deposit_account()
		pe1 = record_advance(cust, amount=10000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_invoice(cust, rate=10000)
		submit_invoice(name)
		link_advance(name, pe1, 10000)  # settles it fully
		si = frappe.get_doc("Sales Invoice", name)
		self.assertAlmostEqual(flt(si.outstanding_amount), 0, places=2)

		pe2 = record_advance(cust, amount=5000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe2, 1000)  # already settled

		name2 = self._draft_invoice(cust, rate=5000)
		submit_invoice(name2)
		cancel_invoice(name2)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name2, pe2, 1000)

	def test_unlink_advance_blocked_on_cancelled_invoice(self):
		from buildsuite_core.api.invoice import cancel_invoice, submit_invoice, unlink_advance

		cust = self._customer()
		name = self._draft_invoice(cust)
		submit_invoice(name)
		cancel_invoice(name)
		with self.assertRaises(frappe.ValidationError):
			unlink_advance(name, "does-not-matter")  # the docstatus==2 guard fires first

	def test_link_advance_accounts_for_amount_committed_on_another_draft(self):
		from buildsuite_core.api.invoice import available_advances, link_advance, record_advance

		cust = self._customer()
		cash = self._deposit_account()
		pe = record_advance(cust, amount=50000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		draft_a = self._draft_invoice(cust, rate=100000)
		draft_b = self._draft_invoice(cust, rate=100000)

		link_advance(draft_a, pe, 30000)  # earmark 30000 on draft A

		avail_on_b = [a for a in available_advances(draft_b) if a["payment_entry"] == pe]
		self.assertEqual(len(avail_on_b), 1)
		self.assertAlmostEqual(avail_on_b[0]["unallocated"], 20000, places=2)  # 50000 - 30000 committed on A

		with self.assertRaises(frappe.ValidationError):
			link_advance(draft_b, pe, 25000)  # exceeds the 20000 actually still free
		link_advance(draft_b, pe, 20000)  # exactly what's left succeeds

	# --- F: minor -------------------------------------------------------------
	def test_income_account_falls_back_when_company_has_no_default(self):
		from buildsuite_core.api.invoice import _income_account

		original = frappe.db.get_value("Company", self.company, "default_income_account")
		frappe.db.set_value("Company", self.company, "default_income_account", None)
		try:
			acct = _income_account(self.company)
			self.assertTrue(acct)
			self.assertEqual(frappe.db.get_value("Account", acct, "company"), self.company)
			self.assertEqual(frappe.db.get_value("Account", acct, "root_type"), "Income")
		finally:
			frappe.db.set_value("Company", self.company, "default_income_account", original)

	def test_available_advances_scoped_to_customer_and_company(self):
		from buildsuite_core.api.invoice import available_advances, record_advance

		cust_a = self._customer()
		cust_b = self._customer()
		cash = self._deposit_account()
		pe_a = record_advance(cust_a, amount=8000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		record_advance(cust_b, amount=9000, date="2026-07-20", deposit_to=cash, mode_of_payment="Cash")
		name = self._draft_invoice(cust_a, rate=1000)
		names = [a["payment_entry"] for a in available_advances(name)]
		self.assertIn(pe_a, names)
		self.assertEqual(len(names), 1)  # cust_b's advance must not appear
