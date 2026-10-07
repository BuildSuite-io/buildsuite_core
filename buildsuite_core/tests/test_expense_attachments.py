# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Expense Entry receipts use Frappe's native document attachments — so a receipt added on the
mobile app or in Desk shows in the SPA, and a receipt uploaded in the SPA shows in Desk/mobile."""

import json

import frappe

from buildsuite_core.tests.base import BuildSuiteTestCase


class TestExpenseAttachments(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _company_account(self):
		return frappe.db.get_value(
			"Account", {"company": self.company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, "name"
		)

	def _expense_account(self):
		return frappe.db.get_value(
			"Account", {"company": self.company, "is_group": 0, "root_type": "Expense"}, "name"
		)

	def _save(self, attachment=None):
		from buildsuite_core.api.expense_entry import save_expense

		row = {"expense_account": self._expense_account(), "amount": 100, "description": "Spend"}
		if attachment:
			row["attachment"] = attachment
		return save_expense(
			json.dumps(
				{
					"project": self.project,
					"paid_from": "company",
					"company_account": self._company_account(),
					"rows": [row],
				}
			)
		)["name"]

	def test_native_attachment_surfaces_in_spa(self):
		"""A receipt attached to the document natively (as the mobile app / Desk do) shows in the
		SPA detail and lights the list's attachment flag."""
		from buildsuite_core.api.expense_entry import get_expense, list_expenses

		name = self._save()
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "mobile-receipt.txt",
				"content": "receipt",
				"attached_to_doctype": "Expense Entry",
				"attached_to_name": name,
			}
		).insert(ignore_permissions=True)

		full = get_expense(name)
		self.assertTrue(any("mobile-receipt" in (a.get("file_name") or "") for a in full["attachments"]))
		row = next(r for r in list_expenses() if r["name"] == name)
		self.assertTrue(row["has_attachment"])

	def test_spa_upload_attaches_natively(self):
		"""A receipt the SPA uploaded (an orphan File referenced by the per-line attachment URL) is
		linked to the Expense Entry natively on save, so Desk + mobile see it too."""
		from buildsuite_core.api.expense_entry import get_expense

		orphan = frappe.get_doc(
			{"doctype": "File", "file_name": "spa-receipt.txt", "content": "spa"}
		).insert(ignore_permissions=True)
		self.assertFalse(orphan.attached_to_name)  # unattached before save

		name = self._save(attachment=orphan.file_url)
		self.assertTrue(
			frappe.db.exists(
				"File",
				{
					"file_url": orphan.file_url,
					"attached_to_doctype": "Expense Entry",
					"attached_to_name": name,
				},
			)
		)
		full = get_expense(name)
		self.assertTrue(any(a["file_url"] == orphan.file_url for a in full["attachments"]))
