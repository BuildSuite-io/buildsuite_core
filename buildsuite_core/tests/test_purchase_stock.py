# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Tests for the project field on ERPNext buying/stock doctypes (Material
Request, Purchase Order, Purchase Receipt, Purchase Invoice, Stock Entry) and
the rate-update confirm endpoint's write + snapshot-immunity guarantees."""

import frappe
from frappe.utils import add_days, nowdate

from buildsuite_core.api import rate_master as rm_api
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestPurchaseStockProjectField(BuildSuiteTestCase):
	def _supplier(self):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"UAT Supplier {self._n}",
				"supplier_group": frappe.db.get_value("Supplier Group", {}, "name"),
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)

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

	def _warehouse(self):
		return frappe.db.get_value("Warehouse", {"is_group": 0, "company": self.company}, "name")

	def test_project_field_present_required_on_material_request(self):
		# BUY-001 — project is present and mandatory on Material Request.
		item = self._item()
		due = add_days(nowdate(), 7)
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": "Material Request",
					"material_request_type": "Purchase",
					"company": self.company,
					"schedule_date": due,
					"items": [{"item_code": item.name, "qty": 1, "schedule_date": due, "rate": 10}],
				}
			).insert(ignore_permissions=True)

		p = self._make_project(company=self.company)
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": self.company,
				"project": p.name,
				"schedule_date": due,
				"items": [{"item_code": item.name, "qty": 1, "schedule_date": due, "rate": 10}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(mr.project, p.name)

	def test_project_field_on_purchase_order(self):
		# BUY-002 — project is present and mandatory on Purchase Order.
		supplier = self._supplier()
		item = self._item()
		due = add_days(nowdate(), 7)
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": "Purchase Order",
					"supplier": supplier.name,
					"company": self.company,
					"schedule_date": due,
					"items": [{"item_code": item.name, "qty": 1, "rate": 10, "schedule_date": due}],
				}
			).insert(ignore_permissions=True)

		p = self._make_project(company=self.company)
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": supplier.name,
				"company": self.company,
				"project": p.name,
				"schedule_date": due,
				"items": [{"item_code": item.name, "qty": 1, "rate": 10, "schedule_date": due}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(po.project, p.name)

	def test_project_field_on_purchase_receipt(self):
		# BUY-003 — project is present and mandatory on Purchase Receipt.
		supplier = self._supplier()
		item = self._item()
		wh = self._warehouse()
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": "Purchase Receipt",
					"supplier": supplier.name,
					"company": self.company,
					"items": [{"item_code": item.name, "qty": 1, "rate": 10, "warehouse": wh}],
				}
			).insert(ignore_permissions=True)

		p = self._make_project(company=self.company)
		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier.name,
				"company": self.company,
				"project": p.name,
				"items": [{"item_code": item.name, "qty": 1, "rate": 10, "warehouse": wh}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(pr.project, p.name)

	def test_project_field_on_purchase_invoice(self):
		# BUY-004 — project is present on Purchase Invoice but OPTIONAL (unlike
		# the other root buying docs): it can be created with no project, and
		# can also carry one when set.
		supplier = self._supplier()
		item = self._item()
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": supplier.name,
				"company": self.company,
				"items": [{"item_code": item.name, "qty": 1, "rate": 10}],
			}
		).insert(ignore_permissions=True)  # no throw
		self.assertFalse(pi.project)

		p = self._make_project(company=self.company)
		pi2 = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": supplier.name,
				"company": self.company,
				"project": p.name,
				"items": [{"item_code": item.name, "qty": 1, "rate": 10}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(pi2.project, p.name)

	def test_project_field_on_stock_entry(self):
		# BUY-005 — project is present and mandatory on Stock Entry.
		item = self._item()
		wh = self._warehouse()
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Receipt",
					"company": self.company,
					"items": [{"item_code": item.name, "qty": 1, "t_warehouse": wh, "basic_rate": 10}],
				}
			).insert(ignore_permissions=True)

		p = self._make_project(company=self.company)
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": self.company,
				"project": p.name,
				"items": [{"item_code": item.name, "qty": 1, "t_warehouse": wh, "basic_rate": 10}],
			}
		).insert(ignore_permissions=True)
		self.assertEqual(se.project, p.name)


class TestRateMasterConfirmEndpoint(BuildSuiteTestCase):
	def test_rate_confirm_writes_rate_and_history_log(self):
		# BUY-025 — confirming a rate update via the PO-submit endpoint writes
		# the new current_rate AND appends a "Purchase-driven" history row
		# (distinct from a plain manual edit's "Manual revision" reason).
		rm = self._make_rate_master(rate=100)
		changed = rm_api.update_rates_from_po(
			purchase_order="PO-UAT-TEST",
			updates=[{"rate_master": rm.name, "new_rate": 150}],
			supplier="UAT Supplier X",
		)
		self.assertEqual(changed, [rm.name])
		rm.reload()
		self.assertEqual(rm.current_rate, 150)
		self.assertEqual(rm.previous_rate, 100)
		new_row = rm.rate_history[-1]
		self.assertEqual(new_row.reason, "Purchase-driven")
		self.assertEqual(new_row.purchase_order, "PO-UAT-TEST")

	def test_estimate_snapshots_unaffected_by_rate_confirm(self):
		# BUY-031 — confirming a rate change through this specific endpoint
		# (not just any direct DB write) still leaves an already-created BOQ
		# Sub Item's snapshot rate untouched.
		p = self._make_project(company=self.company)
		b = frappe.get_doc(
			{"doctype": "BOQ", "project": p.name, "title": "Snap", "margin_rate": 10, "tax_rate": 18}
		).insert(ignore_permissions=True)
		g = frappe.get_doc(
			{"doctype": "BOQ Group", "boq": b.name, "code": "A", "group_name": "Civil"}
		).insert(ignore_permissions=True)
		it = frappe.get_doc(
			{
				"doctype": "BOQ Item",
				"boq": b.name,
				"boq_group": g.name,
				"code": "A.1",
				"description": "x",
				"unit": "Nos",
				"planned_qty": 1,
				"rate": 1,
			}
		).insert(ignore_permissions=True)
		rm = self._make_rate_master(rate=500)
		si = frappe.get_doc(
			{
				"doctype": "BOQ Sub Item",
				"boq": b.name,
				"boq_item": it.name,
				"rate_master": rm.name,
				"description": "s",
				"qty_per_unit": 1,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(si.rate, 500)

		rm_api.update_rates_from_po(
			purchase_order="PO-UAT-TEST-2", updates=[{"rate_master": rm.name, "new_rate": 900}]
		)
		si.reload()
		self.assertEqual(si.rate, 500)  # snapshot unaffected by the later rate confirm
