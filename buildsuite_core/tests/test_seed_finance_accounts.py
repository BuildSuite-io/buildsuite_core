# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Per-company finance account seeding + the configurable Petty Cash Account setting.

Every BuildSuite finance posting (petty cash, expense reimbursements, subcontractor retention,
plant recovery) depends on these ledgers existing — users never configure them, so they are
seeded on install/migrate. The petty-cash float is configurable via BuildSuite Core Settings."""

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestSeedFinanceAccounts(BuildSuiteTestCase):
	def test_seed_company_accounts_creates_ledgers(self):
		from buildsuite_core.install import seed_company_accounts

		seed_company_accounts(self.company)
		expected = {
			"Petty Cash": ("Asset", "Cash"),
			"Petty Cash Advances": ("Asset", ""),
			"Reimbursements Payable": ("Liability", ""),
			"Retention Payable": ("Liability", ""),
			"Plant Recovery": ("Expense", ""),  # contra-expense
			"Cash": ("Asset", "Cash"),
			"Bank": ("Asset", "Bank"),
		}
		for name, (root_type, account_type) in expected.items():
			acc = frappe.db.get_value(
				"Account",
				{"account_name": name, "company": self.company, "is_group": 0},
				["root_type", "account_type"],
				as_dict=True,
			)
			self.assertIsNotNone(acc, f"{name} was not seeded")
			self.assertEqual(acc.root_type, root_type, name)
			self.assertEqual(acc.account_type or "", account_type, name)

	def test_seeding_is_idempotent(self):
		from buildsuite_core.install import seed_company_accounts

		seed_company_accounts(self.company)
		seed_company_accounts(self.company)  # a second pass must not duplicate
		for name in ("Retention Payable", "Plant Recovery", "Petty Cash"):
			rows = frappe.get_all(
				"Account", filters={"account_name": name, "company": self.company, "is_group": 0}
			)
			self.assertEqual(len(rows), 1, f"{name} duplicated")

	def test_default_petty_cash_account_is_seeded(self):
		from buildsuite_core.install import seed_finance_accounts

		frappe.db.set_single_value("BuildSuite Core Settings", "default_petty_cash_account", None)
		seed_finance_accounts()
		value = frappe.db.get_single_value("BuildSuite Core Settings", "default_petty_cash_account")
		self.assertTrue(value)
		self.assertEqual(frappe.db.get_value("Account", value, "account_name"), "Petty Cash")

	def test_petty_cash_account_setting_round_trip(self):
		# The setting keys off the BuildSuite default company, so seed + assert against it.
		from buildsuite_core.api.core_settings import get_core_settings, set_petty_cash_account
		from buildsuite_core.install import seed_company_accounts
		from buildsuite_core.utils.project import default_company

		company = default_company()
		seed_company_accounts(company)
		cash = frappe.db.get_value(
			"Account", {"account_name": "Cash", "company": company, "is_group": 0}, "name"
		)
		set_petty_cash_account(cash)
		settings = get_core_settings()
		self.assertEqual(settings["petty_cash_account"], cash)
		self.assertIn(cash, [o["name"] for o in settings["petty_cash_options"]])

	def test_petty_cash_account_rejects_non_cash_account(self):
		from buildsuite_core.api.core_settings import set_petty_cash_account
		from buildsuite_core.install import seed_company_accounts
		from buildsuite_core.utils.project import default_company

		company = default_company()
		seed_company_accounts(company)
		expense = frappe.db.get_value(
			"Account", {"account_name": "Plant Recovery", "company": company, "is_group": 0}, "name"
		)
		self.assertRaises(frappe.ValidationError, set_petty_cash_account, expense)
