# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""The Subcontractor Charges account belongs under Direct Expenses, not beside it on the root."""

from unittest.mock import patch

import frappe

from buildsuite_core.patches import move_subcontractor_charges_to_direct_expenses as patch_mod
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils import subcontract_billing as billing


class TestSubcontractorChargesAccount(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_value("Project", self._make_project().name, "company")
		self.direct = frappe.db.get_value(
			"Account", {"account_name": "Direct Expenses", "company": self.company, "is_group": 1}, "name"
		)
		self.indirect = frappe.db.get_value(
			"Account", {"account_name": "Indirect Expenses", "company": self.company, "is_group": 1}, "name"
		)
		self.root = frappe.db.get_value("Account", self.direct, "parent_account")
		self.acct = billing.resolve_accounts(self.company)["expense"]

	def _move(self, parent):
		doc = frappe.get_doc("Account", self.acct)
		doc.parent_account = parent
		doc.flags.ignore_permissions = True
		doc.save()

	def _parent(self):
		return frappe.db.get_value("Account", self.acct, "parent_account")

	def test_a_new_account_is_created_under_direct_expenses(self):
		with patch.object(billing, "EXPENSE_ACCOUNT_NAME", "Subcontractor Charges Probe"):
			name = billing.resolve_accounts(self.company)["expense"]
		self.assertEqual(frappe.db.get_value("Account", name, "parent_account"), self.direct)

	def test_falls_back_to_the_root_when_there_is_no_direct_expenses_group(self):
		with patch("frappe.db.exists", return_value=False):
			self.assertEqual(billing.direct_expenses_hint(self.company), "Expenses")

	def test_patch_moves_an_account_left_on_the_root(self):
		self._move(self.root)
		patch_mod.execute()
		self.assertEqual(self._parent(), self.direct)

	def test_patch_leaves_an_account_an_accountant_placed(self):
		self._move(self.indirect)
		patch_mod.execute()
		self.assertEqual(self._parent(), self.indirect)
