# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Amending a cancelled document starts the copy at the workflow's first draft state, as Desk does,
instead of carrying "Cancelled" over (Frappe refuses that: "transition not allowed from Draft to
Cancelled")."""

import frappe
from frappe.model.workflow import get_workflow_name
from frappe.utils import add_days, nowdate

from buildsuite_core.api.procurement_docs import amend_material_request
from buildsuite_core.tests.base import BuildSuiteTestCase
from buildsuite_core.utils.amend import amended_copy


class TestAmendWorkflowState(BuildSuiteTestCase):
	def _cancelled_mr(self):
		"""A Material Request as it is after cancelling through its workflow: docstatus 2 and the
		workflow's Cancelled state (set directly: the test is about the amend, not the walk there)."""
		project = self._make_project().name
		due = add_days(nowdate(), 7)
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"AMEND-{self._n}",
				"item_name": "Amend test item",
				"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
				"stock_uom": "Nos",
			}
		).insert(ignore_permissions=True)
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": self.company,
				"project": project,
				"schedule_date": due,
				"items": [
					{
						"item_code": item.name,
						"qty": 1,
						"schedule_date": due,
						"warehouse": frappe.db.get_value(
							"Warehouse", {"is_group": 0, "company": self.company}, "name"
						),
						"project": project,
					}
				],
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Material Request", mr.name, {"docstatus": 2, "workflow_state": "Cancelled"})
		for row in mr.items:
			frappe.db.set_value(row.doctype, row.name, "docstatus", 2)
		return frappe.get_doc("Material Request", mr.name)

	def _workflow(self):
		name = get_workflow_name("Material Request")
		if not name:
			self.skipTest("no active Material Request workflow on this site")
		return frappe.get_cached_doc("Workflow", name)

	def test_amended_copy_starts_at_the_first_draft_state(self):
		wf = self._workflow()
		first_draft = next(s.state for s in wf.states if str(s.doc_status) == "0")
		src = self._cancelled_mr()
		copy = amended_copy(src)
		self.assertEqual(copy.amended_from, src.name)
		self.assertEqual(copy.docstatus, 0)
		self.assertEqual(copy.get(wf.workflow_state_field), first_draft)

	def test_a_cancelled_material_request_can_be_amended(self):
		wf = self._workflow()
		src = self._cancelled_mr()
		out = amend_material_request(src.name)
		amended = frappe.get_doc("Material Request", out["name"])
		self.assertEqual(amended.amended_from, src.name)
		self.assertEqual(amended.docstatus, 0)
		self.assertNotEqual(amended.get(wf.workflow_state_field), "Cancelled")
