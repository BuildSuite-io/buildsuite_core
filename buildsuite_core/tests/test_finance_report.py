# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Reports — cross-currency rollups. A foreign-currency invoice must roll into
the financial position and the aged ledger in COMPANY currency (its base_* amount), not its raw
transaction amount."""

import json

import frappe
from frappe.utils import flt

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestFinanceReportCurrency(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

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

	def test_foreign_invoice_rolls_up_in_company_currency(self):
		from buildsuite_core.api.finance_report import financial_position, receivables_and_payables
		from buildsuite_core.api.invoice import save_invoice, submit_invoice

		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		foreign = "USD" if company_currency != "USD" else "EUR"

		before = flt(financial_position(company=self.company)["have"]["customersOwe"])

		name = save_invoice(
			json.dumps(
				{
					"customer": self._customer(),
					"project": self.project,
					"date": "2026-07-20",
					"currency": foreign,
					"conversion_rate": 1500,
					"items": [{"description": "Consulting", "qty": 2, "rate": 300}],
				}
			)
		)["name"]
		submit_invoice(name)  # 600 USD → base 900000 company currency

		# The position's "customers owe" rises by the BASE (company-currency) amount, not 600.
		after = flt(financial_position(company=self.company)["have"]["customersOwe"])
		self.assertAlmostEqual(after - before, 900000, delta=1)

		# The aged ledger shows this invoice's outstanding in company currency too.
		row = next(
			r for r in receivables_and_payables(company=self.company)["receivables"] if r["id"] == name
		)
		self.assertAlmostEqual(flt(row["outstanding"]), 900000, delta=1)
