# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the BuildSuite Workspace registry — the backend source of truth for which SPA
workspaces exist, their order/metadata, and which roles may see each one.

This replaces the hand-maintained WORKSPACE_VISIBILITY / WORKSPACE_ORDER / WORKSPACE_META
matrices in frontend/src/data/roles.js + data/workspaces.js. `visible_to` below is
transcribed from that WORKSPACE_VISIBILITY sheet (the personas with a non-null access
level); each persona maps to its managed role via PERSONA_ROLE. Idempotent — safe to run
on every migrate/patch.
"""

import frappe

# Persona id (roles.js / seed_personas slug) -> the single role it manages.
PERSONA_ROLE = {
	"director": "BuildSuite Director",
	"pm": "BuildSuite PM",
	"estimator": "BuildSuite Estimator",
	"qs": "BuildSuite QS",
	"site-engineer": "BuildSuite Site Engineer",
	"foreman": "BuildSuite Foreman",
	"procurement": "BuildSuite Procurement Officer",
	"store-keeper": "BuildSuite Store Keeper",
	"accountant": "BuildSuite Accountant",
	"hr-manager": "BuildSuite HR Manager",
	"admin": "System Manager",
	"bsa": "BuildSuite Administrator",
}

_ALL = tuple(PERSONA_ROLE)

# Canonical workspaces, in sidebar order (list index -> sort_order). `visible_to` = the
# personas whose WORKSPACE_VISIBILITY value is non-null (admin/bsa are on every workspace).
WORKSPACES = [
	# --- BuildSuite (native SPA) workspaces ---
	{
		"slug": "site-execution", "label": "Site Execution", "icon": "🏗️", "route": "/site-execution",
		"description": "Projects, work packages, tasks, schedule.",
		"visible_to": ("director", "pm", "estimator", "qs", "site-engineer", "foreman", "accountant", "admin", "bsa"),
	},
	{
		"slug": "estimation", "label": "Estimation", "icon": "📐", "route": "/estimation",
		"description": "BOQ, Rate Master, revision compare.",
		"visible_to": ("director", "pm", "estimator", "qs", "admin", "bsa"),
	},
	{
		"slug": "procurement", "label": "Procurement", "icon": "🛒", "route": "/procurement",
		"description": "Material requests, supplier follow-up, GRN.",
		"visible_to": ("director", "pm", "site-engineer", "foreman", "procurement", "store-keeper", "accountant", "admin", "bsa"),
	},
	{
		"slug": "subcontract", "label": "Subcontract", "icon": "🤝", "route": "/subcontract",
		"description": "Vendors, work orders, RA bills, retention.",
		"visible_to": ("director", "pm", "estimator", "qs", "site-engineer", "procurement", "accountant", "admin", "bsa"),
	},
	{
		"slug": "workforce", "label": "Workforce", "icon": "👷", "route": "/workforce",
		"description": "Crews, overtime, wages to contractor.",
		"visible_to": ("director", "pm", "site-engineer", "foreman", "accountant", "hr-manager", "admin", "bsa"),
	},
	{
		"slug": "equipment", "label": "Equipment", "icon": "🔧", "route": "/equipment",
		"description": "Plant & machinery register and usage.",
		"visible_to": ("director", "pm", "site-engineer", "foreman", "procurement", "store-keeper", "accountant", "admin", "bsa"),
	},
	{
		"slug": "project-finance", "label": "Project Finance", "icon": "💵", "route": "/project-finance",
		"description": "Petty cash, cost summary, project P&L.",
		"visible_to": _ALL,
	},
	# --- Inherited ERPNext workspaces (link out to the Frappe desk) ---
	{
		"slug": "accounting", "label": "Accounting", "icon": "📊", "route": "/accounting", "group": "erpnext",
		"description": "Inherited from ERPNext.",
		"visible_to": ("director", "pm", "accountant", "admin", "bsa"),
	},
	{
		"slug": "buying", "label": "Buying", "icon": "📥", "route": "/buying", "group": "erpnext",
		"description": "Inherited from ERPNext.",
		"visible_to": ("director", "pm", "procurement", "store-keeper", "accountant", "admin", "bsa"),
	},
	{
		"slug": "stock", "label": "Stock", "icon": "📦", "route": "/stock", "group": "erpnext",
		"description": "Inherited from ERPNext.",
		"visible_to": ("director", "pm", "site-engineer", "procurement", "store-keeper", "accountant", "admin", "bsa"),
	},
	{
		"slug": "assets", "label": "Assets", "icon": "🏭", "route": "/assets", "group": "erpnext",
		"description": "Inherited from ERPNext — extended for Plant & Machinery.",
		"visible_to": ("director", "pm", "site-engineer", "foreman", "accountant", "admin", "bsa"),
	},
	{
		"slug": "hr", "label": "HR", "icon": "👤", "route": "/hr", "group": "erpnext",
		"description": "Inherited from Frappe HR — office staff only.",
		"visible_to": _ALL,
	},
]


def seed_workspaces():
	"""Create/refresh the BuildSuite Workspace records (idempotent). Roles that don't exist
	on the site yet are skipped, so it's safe to run before the permission seed completes."""
	if not frappe.db.exists("DocType", "BuildSuite Workspace"):
		return  # schema not migrated yet

	for order, ws in enumerate(WORKSPACES):
		roles = [PERSONA_ROLE[p] for p in ws["visible_to"] if frappe.db.exists("Role", PERSONA_ROLE[p])]
		doc = (
			frappe.get_doc("BuildSuite Workspace", ws["slug"])
			if frappe.db.exists("BuildSuite Workspace", ws["slug"])
			else frappe.new_doc("BuildSuite Workspace")
		)
		doc.slug = ws["slug"]
		doc.label = ws["label"]
		doc.icon = ws.get("icon", "")
		doc.route = ws.get("route", f"/{ws['slug']}")
		doc.workspace_group = ws.get("group", "buildsuite")
		doc.sort_order = order
		doc.description = ws.get("description", "")
		doc.set("roles", [{"role": r} for r in roles])
		doc.save(ignore_permissions=True)

	frappe.db.commit()
