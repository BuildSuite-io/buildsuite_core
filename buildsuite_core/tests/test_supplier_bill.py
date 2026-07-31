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
					"supplier_name": f"Supp {self._n}",
					"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups",
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
