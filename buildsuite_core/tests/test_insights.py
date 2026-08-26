# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Insights line-dataset endpoint — contract + the parent-permission gate."""

import frappe

from buildsuite_core.api.insights import line_dataset
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestInsightsLineDataset(BuildSuiteTestCase):
	def test_unknown_dataset_returns_empty(self):
		self.assertEqual(line_dataset("not-a-dataset"), [])

	def test_known_datasets_return_lists(self):
		# Each known line dataset returns a list (rows or empty), never errors, and every row
		# carries the flat keys the engine reads.
		for name in ("receiptLines", "consumptionLines", "expenses", "attendance"):
			rows = line_dataset(name)
			self.assertIsInstance(rows, list, name)
			for r in rows:
				self.assertIn("_key", r)
				self.assertIn("date", r)

	def test_gate_blocks_without_parent_read(self):
		# A user with no read on the parent DocType gets an empty list, mirroring the Vue gate.
		# Website User has none of the BuildSuite roles, so every parent read is denied.
		guest = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"insights-nobody-{self._n}@example.com",
				"first_name": "Nobody",
				"send_welcome_email": 0,
				"roles": [],
			}
		).insert(ignore_permissions=True)
		frappe.set_user(guest.name)
		try:
			for name in ("receiptLines", "consumptionLines", "expenses", "attendance"):
				self.assertEqual(line_dataset(name), [], name)
		finally:
			frappe.set_user("Administrator")
