# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.api import subcontract as api
from buildsuite_core.tests.base import BuildSuiteTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestSubcontractorWorkOrder(IntegrationTestCase):
	"""
	Integration tests for SubcontractorWorkOrder.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestSubcontractorWorkOrder(BuildSuiteTestCase):
	"""api/subcontract.py's save/submit/cancel/amend lifecycle for the Work Order
	(SOV), plus its two BOQ-facing feeds (committed_by_cost_code, get_project_cost_codes)."""

	def setUp(self):
		super().setUp()
		# The interactively-configured default company (consistent CoA currency), not
		# the arbitrary first company base picks — this site has several part-configured.
		self.company = frappe.db.get_single_value("Global Defaults", "default_company") or self.company
		self.project = self._make_project(company=self.company).name

	def _subcontractor(self):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"Sub {self._n}",
				"supplier_type": "Subcontractor",
				"supplier_group": "Subcontractor",
				"custom_trade": frappe.db.get_value("Construction Trade", {}, "name"),
			}
		).insert(ignore_permissions=True)

	def _save(self, name=None, sub=None, lines=None, **kw):
		fields = dict(
			name=name,
			subcontractor=sub or self._subcontractor().name,
			project=self.project,
			date="2026-07-20",
			lines=frappe.as_json(
				lines if lines is not None else [{"scope": "Tiling", "uom": "Nos", "qty": 10, "rate": 100}]
			),
		)
		fields.update(kw)
		return api.save_work_order(**fields)

	def test_save_work_order_creates_with_line_totals(self):
		out = self._save(
			lines=[
				{"scope": "Tiling", "uom": "Nos", "qty": 10, "rate": 100},
				{"scope": "Painting", "uom": "Nos", "qty": 5, "rate": 40},
			]
		)
		self.assertEqual(out["lines"][0]["amount"], 1000)
		self.assertEqual(out["lines"][1]["amount"], 200)
		self.assertEqual(out["total_value"], 1200)

	def test_save_work_order_updates_existing_and_replaces_lines(self):
		out = self._save(lines=[{"scope": "Tiling", "uom": "Nos", "qty": 10, "rate": 100}])
		out2 = self._save(
			name=out["name"],
			sub=out["subcontractor"],
			lines=[{"scope": "Painting", "uom": "Nos", "qty": 5, "rate": 40}],
		)
		self.assertEqual(out2["name"], out["name"])
		self.assertEqual(len(out2["lines"]), 1)
		self.assertEqual(out2["lines"][0]["scope"], "Painting")
		self.assertEqual(out2["total_value"], 200)

	def test_work_order_company_anchored_to_project(self):
		out = self._save()
		self.assertEqual(out["company"], self.company)

	def test_submit_work_order_locks_docstatus(self):
		out = self._save()
		before = api.get_work_order(out["name"])
		self.assertEqual(before["actions"], ["edit", "submit", "delete"])

		after = api.submit_work_order(out["name"])
		self.assertEqual(after["docstatus"], 1)
		self.assertEqual(after["status"], "Submitted")
		self.assertEqual(after["actions"], ["record_measurement", "bill_progress", "cancel"])

	def test_cancel_work_order_blocked_when_measurement_book_or_bill_exists(self):
		out = self._save()
		api.submit_work_order(out["name"])
		wo = frappe.get_doc("Subcontractor Work Order", out["name"])
		api.save_measurement_book(
			work_order=wo.name,
			project=self.project,
			date="2026-07-21",
			entries=frappe.as_json([{"description": "m", "work_order_line": wo.lines[0].name, "quantity": 5}]),
		)
		with self.assertRaises(frappe.ValidationError):
			api.cancel_work_order(out["name"])

	def test_cancel_work_order_allowed_when_clean(self):
		out = self._save()
		api.submit_work_order(out["name"])
		result = api.cancel_work_order(out["name"])
		self.assertEqual(result["docstatus"], 2)
		self.assertEqual(result["status"], "Cancelled")

	def test_amend_work_order_creates_draft_copy_linked_back(self):
		out = self._save()
		api.submit_work_order(out["name"])
		api.cancel_work_order(out["name"])

		amended = api.amend_work_order(out["name"])
		self.assertEqual(amended["amended_from"], out["name"])
		self.assertEqual(amended["docstatus"], 0)
		self.assertEqual(len(amended["lines"]), 1)

		original = api.get_work_order(out["name"])
		self.assertEqual(original["status"], "Cancelled")

	def test_amend_work_order_rejects_non_cancelled(self):
		out = self._save()
		api.submit_work_order(out["name"])  # Submitted, not Cancelled
		with self.assertRaises(frappe.ValidationError):
			api.amend_work_order(out["name"])

	def test_committed_by_cost_code_only_counts_submitted(self):
		sub = self._subcontractor().name
		submitted = self._save(
			sub=sub, lines=[{"scope": "A", "uom": "Nos", "qty": 10, "rate": 100, "cost_code_group": "GRP-A"}]
		)
		api.submit_work_order(submitted["name"])
		self._save(  # stays Draft — must not be counted
			sub=sub, lines=[{"scope": "B", "uom": "Nos", "qty": 999, "rate": 999, "cost_code_group": "GRP-A"}]
		)

		result = api.committed_by_cost_code(self.project)
		self.assertEqual(result.get("GRP-A"), 1000)

	def test_get_project_cost_codes_only_approved_boq(self):
		draft_boq = frappe.get_doc(
			{"doctype": "BOQ", "project": self.project, "title": "Draft", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{"doctype": "BOQ Group", "boq": draft_boq.name, "code": "D", "group_name": "DraftGroup"}
		).insert(ignore_permissions=True)

		approved_boq = frappe.get_doc(
			{"doctype": "BOQ", "project": self.project, "title": "Approved", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)
		frappe.db.set_value("BOQ", approved_boq.name, "status", "Approved")
		g = frappe.get_doc(
			{"doctype": "BOQ Group", "boq": approved_boq.name, "code": "A", "group_name": "ApprovedGroup"}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": approved_boq.name,
				"boq_group": g.name,
				"code": "A.1",
				"description": "x",
				"unit": "Nos",
				"planned_qty": 1,
				"rate": 1,
			}
		).insert(ignore_permissions=True)

		labels = [c["label"] for c in api.get_project_cost_codes(self.project)]
		self.assertTrue(any("ApprovedGroup" in label for label in labels))
		self.assertFalse(any("DraftGroup" in label for label in labels))
