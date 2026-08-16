# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Bills — the supplier bill (Purchase Invoice) wrapper: create, submit, pay,
and the unified payables list."""

import json

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestSupplierBill(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

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

	def _cash(self):
		from buildsuite_core.utils.subcontract_billing import _ensure_account

		return _ensure_account(self.company, "Cash", "Asset", "Cash", "Current Assets")

	def test_create_submit_pay(self):
		from buildsuite_core.api.supplier_bill import (
			list_payables,
			list_payments,
			record_payment,
			save_bill,
			submit_bill,
		)

		supp = self._supplier()
		res = save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"bill_no": "INV-SUP-1",
					"items": [{"description": "Cement 100 bags", "qty": 100, "rate": 400}],
				}
			)
		)
		name = res["name"]
		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertEqual(pi.company, self.company)
		self.assertEqual(pi.supplier, supp)
		self.assertEqual(flt(pi.grand_total), 40000)

		submit_bill(name)
		cash = self._cash()
		r = record_payment(name, amount=15000, date="2026-07-25", mode_of_payment="Cash", pay_from=cash)
		self.assertAlmostEqual(r["payment"]["paid"], 15000, places=2)
		self.assertAlmostEqual(r["payment"]["outstanding"], 25000, places=2)
		pe = frappe.get_doc("Payment Entry", r["payment_entry"])
		self.assertEqual(pe.paid_from, cash)
		self.assertEqual(len(list_payments(name)), 1)

		# Unified payables includes it, tagged as a supplier bill.
		mine = [p for p in list_payables(company=self.company) if p["name"] == name]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0]["kind"], "supplier")
		self.assertEqual(mine[0]["status"], "Partly Paid")

	def test_supplier_advance(self):
		from buildsuite_core.api.supplier_bill import payables_summary, record_advance

		supp = self._supplier()
		cash = self._cash()
		before = payables_summary(company=self.company)["advances"]
		r = record_advance(supp, amount=20000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")
		pe = frappe.get_doc("Payment Entry", r["payment_entry"])
		self.assertEqual(pe.payment_type, "Pay")
		self.assertEqual(pe.party, supp)
		self.assertAlmostEqual(flt(pe.unallocated_amount), 20000, places=2)
		self.assertAlmostEqual(payables_summary(company=self.company)["advances"] - before, 20000, places=2)

	def _draft_bill(self, supp, rate=50000):
		from buildsuite_core.api.supplier_bill import save_bill

		return save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"due_date": "2026-08-20",
					"items": [{"description": "Material", "qty": 1, "rate": rate}],
				}
			)
		)["name"]

	def test_link_advance_on_draft_bill(self):
		"""A supplier advance adjusted against a DRAFT bill lands in the native `advances` table,
		reduces outstanding, drops out of 'available' once used, and cannot be over-linked."""
		from buildsuite_core.api.supplier_bill import (
			available_advances,
			get_bill,
			link_advance,
			record_advance,
			submit_bill,
			unlink_advance,
		)

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=30000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=50000)

		self.assertAlmostEqual(
			[a for a in available_advances(name) if a["payment_entry"] == pe][0]["unallocated"],
			30000,
			places=2,
		)
		link_advance(name, pe, 20000)
		data = get_bill(name)
		self.assertEqual(len(data["advances"]), 1)
		self.assertAlmostEqual(data["advance_adjusted"], 20000, places=2)
		self.assertAlmostEqual(
			flt(frappe.get_doc("Purchase Invoice", name).outstanding_amount), 30000, places=2
		)
		# 10000 left, not the full 30000
		self.assertAlmostEqual(
			[a for a in available_advances(name) if a["payment_entry"] == pe][0]["unallocated"],
			10000,
			places=2,
		)

		unlink_advance(name, pe)
		self.assertEqual(len(get_bill(name)["advances"]), 0)

		# Re-link and submit — must not raise "Allocated amount cannot be greater than unadjusted".
		link_advance(name, pe, 20000)
		submit_bill(name)
		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertEqual(pi.docstatus, 1)
		self.assertAlmostEqual(flt(pi.outstanding_amount), 30000, places=2)
		self.assertAlmostEqual(get_bill(name)["advance_adjusted"], 20000, places=2)

	def test_supplier_advance_multi_step_on_submitted(self):
		"""Adjusting the SAME advance against a submitted bill in several steps sums into ONE
		Advance Payments line, excluded from cash payments; unlink reverts everything."""
		from buildsuite_core.api.supplier_bill import (
			get_bill,
			link_advance,
			list_payments,
			record_advance,
			submit_bill,
			unlink_advance,
		)

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=70000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=60000)
		submit_bill(name)

		link_advance(name, pe, 10000)
		link_advance(name, pe, 15000)  # same advance, two steps → 25000 total
		data = get_bill(name)
		adv_rows = [a for a in data["advances"] if a["payment_entry"] == pe]
		self.assertEqual(len(adv_rows), 1)
		self.assertAlmostEqual(adv_rows[0]["allocated"], 25000, places=2)
		self.assertAlmostEqual(data["advance_adjusted"], 25000, places=2)
		self.assertAlmostEqual(data["payment"]["paid"], 0, places=2)
		self.assertEqual(len(list_payments(name)), 0)
		self.assertAlmostEqual(
			flt(frappe.get_doc("Purchase Invoice", name).outstanding_amount), 35000, places=2
		)

		unlink_advance(name, pe)
		self.assertAlmostEqual(
			flt(frappe.get_doc("Purchase Invoice", name).outstanding_amount), 60000, places=2
		)
		self.assertAlmostEqual(
			flt(frappe.db.get_value("Payment Entry", pe, "unallocated_amount")), 70000, places=2
		)
		self.assertEqual(len(get_bill(name)["advances"]), 0)

	# --- extra fixtures for the additions below ------------------------------
	def _item(self):
		return frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"UAT-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
				"item_name": "UAT Stock Item",
				"item_group": frappe.db.get_value("Item Group", {}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert(ignore_permissions=True)

	def _submitted_po(self, supp, qty=10, rate=1000):
		item = self._item()
		due = frappe.utils.add_days(frappe.utils.nowdate(), 7)
		wh = frappe.db.get_value("Warehouse", {"is_group": 0, "company": self.company}, "name")
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supp,
				"company": self.company,
				"project": self.project,
				"transaction_date": "2026-07-01",
				"schedule_date": due,
				"items": [
					{"item_code": item.name, "qty": qty, "rate": rate, "schedule_date": due, "warehouse": wh}
				],
			}
		).insert(ignore_permissions=True)
		po.submit()
		return po

	# --- A: cancel / delete / payables summary --------------------------------
	def test_cancel_bill_reflects_in_summary_and_blocks_advances(self):
		from buildsuite_core.api.supplier_bill import (
			cancel_bill,
			get_bill,
			link_advance,
			record_advance,
			submit_bill,
			unlink_advance,
		)

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=10000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=50000)
		submit_bill(name)
		cancel_bill(name)

		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertEqual(pi.docstatus, 2)
		data = get_bill(name)
		self.assertEqual(data["payment"]["status"], "Cancelled")

		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 1000)
		with self.assertRaises(frappe.ValidationError):
			unlink_advance(name, pe)

	def test_delete_bill_requires_draft(self):
		from buildsuite_core.api.supplier_bill import delete_bill, submit_bill

		supp = self._supplier()
		name = self._draft_bill(supp)
		delete_bill(name)
		self.assertFalse(frappe.db.exists("Purchase Invoice", name))

		name2 = self._draft_bill(supp)
		submit_bill(name2)
		with self.assertRaises(frappe.ValidationError):
			delete_bill(name2)

	def test_payables_summary_aggregates_outstanding_and_advances(self):
		from buildsuite_core.api.supplier_bill import payables_summary, record_advance, submit_bill

		supp = self._supplier()
		cash = self._cash()
		before = payables_summary(company=self.company)
		name = self._draft_bill(supp, rate=30000)
		submit_bill(name)
		record_advance(supp, amount=5000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")

		after = payables_summary(company=self.company)
		self.assertAlmostEqual(after["outstanding"] - before["outstanding"], 30000, places=2)
		self.assertAlmostEqual(after["advances"] - before["advances"], 5000, places=2)

	# --- B: save_bill — untested branches -------------------------------------
	def test_save_bill_edit_existing_draft_replaces_lines(self):
		from buildsuite_core.api.supplier_bill import save_bill

		supp = self._supplier()
		name = self._draft_bill(supp, rate=10000)
		save_bill(
			json.dumps(
				{
					"name": name,
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "New Line", "qty": 2, "rate": 5000}],
				}
			)
		)
		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertEqual(len(pi.items), 1)
		self.assertEqual(pi.items[0].description, "New Line")
		self.assertAlmostEqual(flt(pi.grand_total), 10000, places=2)

	def test_save_bill_requires_supplier_and_at_least_one_line(self):
		from buildsuite_core.api.supplier_bill import save_bill

		supp = self._supplier()
		with self.assertRaises(frappe.ValidationError):
			save_bill(
				json.dumps(
					{
						"project": self.project,
						"date": "2026-07-20",
						"items": [{"description": "x", "qty": 1, "rate": 100}],
					}
				)
			)
		with self.assertRaises(frappe.ValidationError):
			save_bill(
				json.dumps({"supplier": supp, "project": self.project, "date": "2026-07-20", "items": []})
			)

	def test_save_bill_edit_only_while_draft(self):
		from buildsuite_core.api.supplier_bill import save_bill, submit_bill

		supp = self._supplier()
		name = self._draft_bill(supp)
		submit_bill(name)
		with self.assertRaises(frappe.ValidationError):
			save_bill(
				json.dumps(
					{
						"name": name,
						"supplier": supp,
						"project": self.project,
						"date": "2026-07-20",
						"items": [{"description": "x", "qty": 1, "rate": 999}],
					}
				)
			)

	def test_save_bill_cross_company_tax_account_rejected(self):
		from buildsuite_core.api.supplier_bill import save_bill

		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		other_acct = frappe.db.get_value(
			"Account", {"company": other, "is_group": 0, "root_type": "Liability"}, "name"
		)
		if not other_acct:
			self.skipTest("no cross-company account")
		supp = self._supplier()
		with self.assertRaises(frappe.ValidationError):
			save_bill(
				json.dumps(
					{
						"supplier": supp,
						"project": self.project,
						"date": "2026-07-20",
						"items": [{"description": "x", "qty": 1, "rate": 1000}],
						"taxes": [{"charge_type": "On Net Total", "account_head": other_acct, "rate": 5}],
					}
				)
			)

	def test_save_bill_discount_modes(self):
		from buildsuite_core.api.supplier_bill import save_bill

		supp = self._supplier()
		res = save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 100000}],
					"discount_amount": 10000,
				}
			)
		)
		pi = frappe.get_doc("Purchase Invoice", res["name"])
		self.assertAlmostEqual(flt(pi.grand_total), 90000, places=2)

		res2 = save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 100000}],
					"additional_discount_on": "Grand Total",
					"additional_discount_percentage": 10,
				}
			)
		)
		pi2 = frappe.get_doc("Purchase Invoice", res2["name"])
		self.assertEqual(pi2.apply_discount_on, "Grand Total")
		self.assertAlmostEqual(flt(pi2.grand_total), 90000, places=2)

	def test_save_bill_tax_template_expands_rows(self):
		from buildsuite_core.api.supplier_bill import save_bill

		tax_acct = frappe.db.get_value(
			"Account", {"company": self.company, "account_type": "Tax", "is_group": 0}, "name"
		)
		if not tax_acct:
			from buildsuite_core.utils.subcontract_billing import _ensure_account

			tax_acct = _ensure_account(self.company, "Input Tax", "Liability", "Tax", "Duties and Taxes")

		template = frappe.get_doc(
			{
				"doctype": "Purchase Taxes and Charges Template",
				"title": f"UAT Template {self._n}",
				"company": self.company,
				"taxes": [
					{"charge_type": "On Net Total", "account_head": tax_acct, "description": "Tax", "rate": 8}
				],
			}
		).insert(ignore_permissions=True)

		supp = self._supplier()
		res = save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"items": [{"description": "x", "qty": 1, "rate": 100000}],
					"taxes_and_charges": template.name,
				}
			)
		)
		pi = frappe.get_doc("Purchase Invoice", res["name"])
		self.assertEqual(len(pi.taxes), 1)
		self.assertEqual(pi.taxes[0].account_head, tax_acct)
		self.assertAlmostEqual(flt(pi.grand_total), 108000, places=2)

	# --- C: record_payment gaps -------------------------------------------------
	def test_record_payment_requires_submitted_bill(self):
		from buildsuite_core.api.supplier_bill import record_payment

		supp = self._supplier()
		name = self._draft_bill(supp)
		with self.assertRaises(frappe.ValidationError):
			record_payment(name, amount=1000, pay_from=self._cash())

	def test_record_payment_rejects_cross_company_pay_from(self):
		from buildsuite_core.api.supplier_bill import record_payment, submit_bill

		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if not other:
			self.skipTest("needs a second company")
		other_acct = frappe.db.get_value(
			"Account", {"company": other, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
		)
		if not other_acct:
			self.skipTest("no cross-company bank/cash account")

		supp = self._supplier()
		name = self._draft_bill(supp, rate=10000)
		submit_bill(name)
		with self.assertRaises(frappe.ValidationError):
			record_payment(name, amount=1000, pay_from=other_acct)

	def test_record_payment_default_pay_from_account(self):
		from buildsuite_core.api.supplier_bill import record_payment, submit_bill

		supp = self._supplier()
		name = self._draft_bill(supp, rate=25000)
		submit_bill(name)
		# No amount given -> defaults to the bill's full outstanding.
		r = record_payment(name, pay_from=self._cash(), mode_of_payment="Cash")
		self.assertAlmostEqual(r["payment"]["paid"], 25000, places=2)
		self.assertAlmostEqual(r["payment"]["outstanding"], 0, places=2)

	def test_record_payment_marks_paid_when_fully_settled(self):
		from buildsuite_core.api.supplier_bill import record_payment, submit_bill

		supp = self._supplier()
		name = self._draft_bill(supp, rate=15000)
		submit_bill(name)
		r = record_payment(name, amount=15000, pay_from=self._cash(), mode_of_payment="Cash")
		self.assertEqual(r["payment"]["status"], "Paid")

	# --- D: record_advance guards -----------------------------------------------
	def test_record_advance_validation_guards(self):
		from buildsuite_core.api.supplier_bill import record_advance

		cash = self._cash()
		with self.assertRaises(frappe.ValidationError):
			record_advance(None, amount=1000, pay_from=cash)
		supp = self._supplier()
		with self.assertRaises(frappe.ValidationError):
			record_advance(supp, amount=0, pay_from=cash)
		with self.assertRaises(frappe.ValidationError):
			record_advance(supp, amount=1000, pay_from=None)

		other = frappe.db.get_value("Company", {"name": ["!=", self.company]}, "name")
		if other:
			other_acct = frappe.db.get_value(
				"Account", {"company": other, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
			)
			if other_acct:
				with self.assertRaises(frappe.ValidationError):
					record_advance(supp, amount=1000, pay_from=other_acct)

	# --- E: link_advance / unlink_advance ---------------------------------------
	def test_link_advance_rejects_non_advance_or_wrong_supplier(self):
		from buildsuite_core.api.supplier_bill import link_advance, record_advance

		supp = self._supplier()
		other_supp = self._supplier()
		cash = self._cash()
		pe = record_advance(
			other_supp, amount=10000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash"
		)["payment_entry"]
		name = self._draft_bill(supp, rate=5000)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 1000)  # PE belongs to a different supplier

	def test_link_advance_rejects_over_allocation_beyond_pe_room(self):
		from buildsuite_core.api.supplier_bill import link_advance, record_advance

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=5000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=50000)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 10000)  # more than the PE's 5000 unallocated

	def test_link_advance_bill_room_is_the_binding_cap(self):
		from buildsuite_core.api.supplier_bill import link_advance, record_advance

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=100000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=20000)  # the bill total is the binding constraint here
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 30000)  # the PE has plenty, but the bill can only take 20000
		link_advance(name, pe, 20000)  # exactly the bill total succeeds
		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertAlmostEqual(flt(pi.outstanding_amount), 0, places=2)

	def test_link_advance_partial_relink_room_message(self):
		from buildsuite_core.api.supplier_bill import link_advance, record_advance

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=100000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=50000)
		link_advance(name, pe, 30000)  # room left afterward = 20000 (bill-side)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe, 25000)  # exceeds the remaining 20000 room (but room > 0)
		link_advance(name, pe, 20000)  # exactly the remaining room succeeds

	def test_link_advance_blocked_on_settled_or_cancelled_bill(self):
		from buildsuite_core.api.supplier_bill import (
			cancel_bill,
			link_advance,
			record_advance,
			submit_bill,
		)

		supp = self._supplier()
		cash = self._cash()
		pe1 = record_advance(supp, amount=10000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=10000)
		submit_bill(name)
		link_advance(name, pe1, 10000)  # settles it fully
		pi = frappe.get_doc("Purchase Invoice", name)
		self.assertAlmostEqual(flt(pi.outstanding_amount), 0, places=2)

		pe2 = record_advance(supp, amount=5000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		with self.assertRaises(frappe.ValidationError):
			link_advance(name, pe2, 1000)  # already settled

		name2 = self._draft_bill(supp, rate=5000)
		submit_bill(name2)
		cancel_bill(name2)
		with self.assertRaises(frappe.ValidationError):
			link_advance(name2, pe2, 1000)

	def test_unlink_advance_blocked_on_cancelled_bill(self):
		from buildsuite_core.api.supplier_bill import cancel_bill, submit_bill, unlink_advance

		supp = self._supplier()
		name = self._draft_bill(supp)
		submit_bill(name)
		cancel_bill(name)
		with self.assertRaises(frappe.ValidationError):
			unlink_advance(name, "does-not-matter")  # the docstatus==2 guard fires first

	def test_link_advance_accounts_for_amount_committed_on_another_draft(self):
		from buildsuite_core.api.supplier_bill import available_advances, link_advance, record_advance

		supp = self._supplier()
		cash = self._cash()
		pe = record_advance(supp, amount=50000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		draft_a = self._draft_bill(supp, rate=100000)
		draft_b = self._draft_bill(supp, rate=100000)

		link_advance(draft_a, pe, 30000)  # earmark 30000 on draft A

		avail_on_b = [a for a in available_advances(draft_b) if a["payment_entry"] == pe]
		self.assertEqual(len(avail_on_b), 1)
		self.assertAlmostEqual(avail_on_b[0]["unallocated"], 20000, places=2)  # 50000 - 30000 on A

		with self.assertRaises(frappe.ValidationError):
			link_advance(draft_b, pe, 25000)  # exceeds the 20000 actually still free
		link_advance(draft_b, pe, 20000)  # exactly what's left succeeds

	# --- F: list_payables / list_payments ---------------------------------------
	def test_list_payables_pay_status_branches(self):
		from buildsuite_core.api.supplier_bill import cancel_bill, list_payables, record_payment, submit_bill

		supp = self._supplier()
		cash = self._cash()

		draft_name = self._draft_bill(supp, rate=3000)

		unpaid_name = self._draft_bill(supp, rate=10000)
		submit_bill(unpaid_name)

		paid_name = self._draft_bill(supp, rate=5000)
		submit_bill(paid_name)
		record_payment(paid_name, amount=5000, date="2026-07-25", mode_of_payment="Cash", pay_from=cash)

		cancelled_name = self._draft_bill(supp, rate=2000)
		submit_bill(cancelled_name)
		cancel_bill(cancelled_name)

		rows = {p["name"]: p for p in list_payables(company=self.company)}
		self.assertEqual(rows[draft_name]["status"], "Draft")
		self.assertEqual(rows[unpaid_name]["status"], "Unpaid")
		self.assertEqual(rows[paid_name]["status"], "Paid")
		# A cancelled bill drops out of the payables list entirely (docstatus < 2 filter).
		self.assertNotIn(cancelled_name, rows)

	def test_list_payments_excludes_advance_but_keeps_plain_payment(self):
		from buildsuite_core.api.supplier_bill import (
			link_advance,
			list_payments,
			record_advance,
			record_payment,
			submit_bill,
		)

		supp = self._supplier()
		cash = self._cash()
		# Advance for MORE than what gets linked here, so it still carries unallocated
		# money afterward — that's what distinguishes an advance from a plain payment.
		pe_adv = record_advance(supp, amount=30000, date="2026-07-20", pay_from=cash, mode_of_payment="Cash")[
			"payment_entry"
		]
		name = self._draft_bill(supp, rate=50000)
		submit_bill(name)
		link_advance(name, pe_adv, 20000)
		record_payment(name, amount=10000, date="2026-07-25", mode_of_payment="Cash", pay_from=cash)

		payments = list_payments(name)
		self.assertEqual(len(payments), 1)
		self.assertAlmostEqual(payments[0]["amount"], 10000, places=2)

	# --- G: PO-linking chain -----------------------------------------------------
	def test_list_billable_purchase_orders_filters_by_status_and_per_billed(self):
		from buildsuite_core.api.supplier_bill import list_billable_purchase_orders

		supp = self._supplier()
		po = self._submitted_po(supp, qty=10, rate=1000)
		names = [p["name"] for p in list_billable_purchase_orders(company=self.company)]
		self.assertIn(po.name, names)

		# Fully billed (per_billed=100) drops out of the picker.
		frappe.db.set_value("Purchase Order", po.name, "per_billed", 100)
		names_after = [p["name"] for p in list_billable_purchase_orders(company=self.company)]
		self.assertNotIn(po.name, names_after)

	def test_get_po_bill_lines_returns_remaining_qty_with_po_links(self):
		from buildsuite_core.api.supplier_bill import get_po_bill_lines

		supp = self._supplier()
		po = self._submitted_po(supp, qty=10, rate=1000)
		data = get_po_bill_lines(po.name)
		self.assertEqual(data["supplier"], supp)
		self.assertEqual(data["project"], self.project)
		self.assertEqual(len(data["lines"]), 1)
		line = data["lines"][0]
		self.assertEqual(flt(line["qty"]), 10)
		self.assertEqual(flt(line["rate"]), 1000)
		self.assertEqual(line["purchase_order"], po.name)
		self.assertTrue(line["po_detail"])

	def test_save_bill_from_po_lines_updates_po_per_billed_on_submit(self):
		from buildsuite_core.api.supplier_bill import get_po_bill_lines, save_bill, submit_bill

		supp = self._supplier()
		po = self._submitted_po(supp, qty=10, rate=1000)
		line = get_po_bill_lines(po.name)["lines"][0]

		res = save_bill(
			json.dumps(
				{
					"supplier": supp,
					"project": self.project,
					"date": "2026-07-20",
					"items": [
						{
							"item_code": line["item_code"],
							"description": line["description"],
							"qty": line["qty"],
							"uom": line["uom"],
							"rate": line["rate"],
							"purchase_order": line["purchase_order"],
							"po_detail": line["po_detail"],
						}
					],
				}
			)
		)
		submit_bill(res["name"])

		po.reload()
		self.assertAlmostEqual(flt(po.per_billed), 100, places=1)
		pi_item = frappe.get_doc("Purchase Invoice", res["name"]).items[0]
		self.assertEqual(pi_item.purchase_order, po.name)
		self.assertEqual(pi_item.po_detail, line["po_detail"])
