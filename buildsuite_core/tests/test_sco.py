# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Scope Change Order approval workflow + its activity audit trail."""

import frappe

from buildsuite_core.api.sco import approve_sco, reject_sco, revise_sco
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestScopeChangeOrder(BuildSuiteTestCase):
	def _make_sco(self):
		project = self._make_project(company=self.company)
		return frappe.get_doc(
			{
				"doctype": "Scope Change Order",
				"project": project.name,
				"title": f"SCO {self._n}",
				"type": "Design Change",
				"status": "Pending Approval",
			}
		).insert(ignore_permissions=True)

	def test_activity_log_records_each_transition(self):
		sco = self._make_sco()
		reject_sco(sco.name, "needs costing")
		revise_sco(sco.name)
		approve_sco(sco.name)

		doc = frappe.get_doc("Scope Change Order", sco.name)
		rows = doc.scope_change_order_activity
		self.assertEqual(
			[(r.action, r.comment) for r in rows],
			[("Rejected", "needs costing"), ("Revised", None), ("Approved", None)],
		)
		# every entry stamps who + when
		self.assertTrue(all(r.user == "Administrator" for r in rows))
		self.assertTrue(all(r.activity_on for r in rows))
