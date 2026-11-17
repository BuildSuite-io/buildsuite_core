"""Add the Sales workspace to existing sites without re-seeding admin-customized workspaces."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "BuildSuite Workspace"):
		return

	if frappe.db.exists("BuildSuite Workspace", "sales"):
		return

	persona_roles = {
		"BuildSuite Director",
		"System Manager",
		"BuildSuite Administrator",
	}
	roles = [
		{"role": role, "access": "full"} for role in sorted(persona_roles) if frappe.db.exists("Role", role)
	]
	next_order = frappe.db.sql("select coalesce(max(sort_order), -1) + 1 from `tabBuildSuite Workspace`")[0][
		0
	]
	frappe.get_doc(
		{
			"doctype": "BuildSuite Workspace",
			"slug": "sales",
			"label": "Sales",
			"icon": "📈",
			"route": "/sales",
			"workspace_group": "buildsuite",
			"sort_order": next_order,
			"description": "Customers, quotations, tenders, and payment terms.",
			"roles": roles,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache()
	print("seed_sales_workspace: added Sales to the workspace registry")
