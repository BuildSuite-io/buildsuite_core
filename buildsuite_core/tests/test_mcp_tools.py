# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""MCP tool tests. Tools are plain @mcp.tool()-decorated functions (the decorator
returns fn unchanged), so they're called directly here — no JSON-RPC envelope
needed. The point of these tests is the permission scoping, not the MCP
plumbing (frappe_mcp's own test suite covers the JSON-RPC layer)."""

import frappe

from buildsuite_core.mcp_tools.aggr import get_item_consumption, get_material_received
from buildsuite_core.mcp_tools.list import list_projects
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestMcpTools(BuildSuiteTestCase):
	def _make_persona_user(self, persona, prefix):
		email = f"{prefix}-{self._n}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": prefix.upper(),
				"send_welcome_email": 0,
				"user_type": "System User",
				"persona": persona,
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		return email

	def _project_with_member(self, user):
		return frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"MCP {self._n}",
				"custom_project_id": f"MCP-{self._n}",
				"project_status": "Ongoing",
				"company": self.company,
				"custom_team_members": [{"user": user}],
			}
		).insert(ignore_permissions=True)

	def test_list_projects_scoped(self):
		se = self._make_persona_user("Site Engineer", "mcplist")
		mine = self._project_with_member(se)
		self._make_project(company=self.company)  # not on the team — must not appear

		frappe.set_user(se)
		try:
			names = {row["name"] for row in list_projects()}
			self.assertIn(mine.name, names)
		finally:
			frappe.set_user("Administrator")


class TestMcpAggrTools(BuildSuiteTestCase):
	def _make_persona_user(self, persona, prefix):
		email = f"{prefix}-{self._n}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": prefix.upper(),
				"send_welcome_email": 0,
				"user_type": "System User",
				"persona": persona,
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		return email

	def _item(self):
		return frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": f"MCP-ITEM-{self._n}-{frappe.generate_hash(length=4)}",
				"item_name": "MCP Stock Item",
				"item_group": frappe.db.get_value("Item Group", {}, "name"),
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert(ignore_permissions=True)

	def _warehouse(self):
		return frappe.db.get_value("Warehouse", {"is_group": 0, "company": self.company}, "name")

	def _supplier(self):
		return frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": f"MCP Supplier {self._n}",
				"supplier_group": frappe.db.get_value("Supplier Group", {}, "name"),
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)

	def _submit_stock_entry(self, entry_type, project, item, qty, s_warehouse=None, t_warehouse=None):
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": entry_type,
				"company": self.company,
				"project": project,
				"items": [
					{
						"item_code": item,
						"qty": qty,
						"s_warehouse": s_warehouse,
						"t_warehouse": t_warehouse,
						"basic_rate": 10,
					}
				],
			}
		).insert(ignore_permissions=True)
		se.submit()
		return se

	def _submit_purchase_receipt(self, project, supplier, item, qty, rate=100):
		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": supplier,
				"company": self.company,
				"project": project,
				"items": [{"item_code": item, "qty": qty, "rate": rate, "warehouse": self._warehouse()}],
			}
		).insert(ignore_permissions=True)
		pr.submit()
		return pr

	def test_get_item_consumption_sums_material_issues(self):
		p = self._make_project(company=self.company)
		item = self._item()
		wh = self._warehouse()
		self._submit_stock_entry("Material Receipt", p.name, item.name, qty=20, t_warehouse=wh)
		self._submit_stock_entry("Material Issue", p.name, item.name, qty=6, s_warehouse=wh)
		self._submit_stock_entry("Material Issue", p.name, item.name, qty=4, s_warehouse=wh)

		result = get_item_consumption(project=p.name, item_code=item.name)
		self.assertEqual(result["qty_issued"], 10)

	def test_get_item_consumption_denied_outside_team(self):
		outsider = self._make_persona_user("Site Engineer", "mcpconsume")
		p = self._make_project(company=self.company)  # outsider not on the team

		frappe.set_user(outsider)
		try:
			self.assertRaises(frappe.PermissionError, get_item_consumption, project=p.name, item_code="whatever")
		finally:
			frappe.set_user("Administrator")

	def test_get_material_received_sums_purchase_receipts(self):
		p = self._make_project(company=self.company)
		supplier = self._supplier()
		item = self._item()
		self._submit_purchase_receipt(p.name, supplier.name, item.name, qty=8)
		self._submit_purchase_receipt(p.name, supplier.name, item.name, qty=5)

		result = get_material_received(project=p.name, item_code=item.name)
		self.assertEqual(result["qty_received"], 13)

	def test_get_material_received_denied_outside_team(self):
		outsider = self._make_persona_user("Site Engineer", "mcpreceived")
		p = self._make_project(company=self.company)  # outsider not on the team

		frappe.set_user(outsider)
		try:
			self.assertRaises(frappe.PermissionError, get_material_received, project=p.name, item_code="whatever")
		finally:
			frappe.set_user("Administrator")
