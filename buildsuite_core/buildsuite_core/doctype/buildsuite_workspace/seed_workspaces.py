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

# Canonical workspaces, in sidebar order (list index -> sort_order). `visibility` = the
# WORKSPACE_VISIBILITY sheet: persona -> access hint (the persona is visible when present;
# the hint is cosmetic only). admin/bsa are on every workspace as "full".
WORKSPACES = [
	# --- BuildSuite (native SPA) workspaces ---
	{
		"slug": "site-execution", "label": "Site Execution", "icon": "🏗️", "route": "/site-execution",
		"description": "Projects, work packages, tasks, schedule.",
		"visibility": {
			"director": "full", "pm": "full", "estimator": "read", "qs": "read",
			"site-engineer": "full", "foreman": "create-own", "accountant": "read",
			"admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "estimation", "label": "Estimation", "icon": "📐", "route": "/estimation",
		"description": "BOQ, Rate Master, revision compare.",
		"visibility": {
			"director": "full", "pm": "read", "estimator": "full", "qs": "full",
			"admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "procurement", "label": "Procurement", "icon": "🛒", "route": "/procurement",
		"description": "Material requests, supplier follow-up, GRN.",
		"visibility": {
			"director": "full", "pm": "approve", "site-engineer": "create-own",
			"foreman": "create-own", "procurement": "full", "store-keeper": "full",
			"accountant": "read", "admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "subcontract", "label": "Subcontract", "icon": "🤝", "route": "/subcontract",
		"description": "Vendors, work orders, RA bills, retention.",
		"visibility": {
			"director": "full", "pm": "approve", "estimator": "read", "qs": "full",
			"site-engineer": "read", "procurement": "full", "accountant": "read",
			"admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "workforce", "label": "Workforce", "icon": "👷", "route": "/workforce",
		"description": "Crews, overtime, wages to contractor.",
		"visibility": {
			"director": "read", "pm": "approve", "site-engineer": "full", "foreman": "full",
			"accountant": "read", "hr-manager": "full", "admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "equipment", "label": "Equipment", "icon": "🔧", "route": "/equipment",
		"description": "Plant & machinery register and usage.",
		"visibility": {
			"director": "read", "pm": "approve", "site-engineer": "full", "foreman": "full",
			"procurement": "full", "store-keeper": "full", "accountant": "read",
			"admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "project-finance", "label": "Project Finance", "icon": "💵", "route": "/project-finance",
		"description": "Petty cash, cost summary, project P&L.",
		"visibility": {
			"director": "full", "pm": "full", "estimator": "self-service", "qs": "read",
			"site-engineer": "self-service", "foreman": "self-service", "procurement": "self-service",
			"store-keeper": "self-service", "accountant": "full", "hr-manager": "self-service",
			"admin": "full", "bsa": "full",
		},
	},
	# --- Inherited ERPNext workspaces (link out to the Frappe desk) ---
	{
		"slug": "accounting", "label": "Accounting", "icon": "📊", "route": "/accounting", "group": "erpnext",
		"description": "Inherited from ERPNext.",
		"visibility": {"director": "full", "pm": "read", "accountant": "full", "admin": "full", "bsa": "full"},
	},
	{
		"slug": "buying", "label": "Buying", "icon": "📥", "route": "/buying", "group": "erpnext",
		"description": "Inherited from ERPNext.",
		"visibility": {
			"director": "full", "pm": "read", "procurement": "full", "store-keeper": "read",
			"accountant": "read", "admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "stock", "label": "Stock", "icon": "📦", "route": "/stock", "group": "erpnext",
		"description": "Inherited from ERPNext.",
		"visibility": {
			"director": "full", "pm": "read", "site-engineer": "read", "procurement": "read",
			"store-keeper": "full", "accountant": "read", "admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "assets", "label": "Assets", "icon": "🏭", "route": "/assets", "group": "erpnext",
		"description": "Inherited from ERPNext — extended for Plant & Machinery.",
		"visibility": {
			"director": "full", "pm": "read", "site-engineer": "read", "foreman": "read",
			"accountant": "full", "admin": "full", "bsa": "full",
		},
	},
	{
		"slug": "hr", "label": "HR", "icon": "👤", "route": "/hr", "group": "erpnext",
		"description": "Inherited from Frappe HR — office staff only.",
		"visibility": {
			"director": "full", "pm": "read", "estimator": "self-service", "qs": "self-service",
			"site-engineer": "self-service", "foreman": "self-service", "procurement": "self-service",
			"store-keeper": "self-service", "accountant": "full", "hr-manager": "full",
			"admin": "full", "bsa": "full",
		},
	},
]


def seed_workspaces():
	"""Create/refresh the BuildSuite Workspace records (idempotent). Roles that don't exist
	on the site yet are skipped, so it's safe to run before the permission seed completes."""
	if not frappe.db.exists("DocType", "BuildSuite Workspace"):
		return  # schema not migrated yet

	for order, ws in enumerate(WORKSPACES):
		roles = [
			{"role": PERSONA_ROLE[p], "access": level}
			for p, level in ws["visibility"].items()
			if frappe.db.exists("Role", PERSONA_ROLE[p])
		]
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
		doc.set("roles", roles)
		doc.save(ignore_permissions=True)

	seed_workspace_shortcuts()
	frappe.db.commit()


# Per-workspace quick-nav shortcut tiles (formerly the client-side seed.js workspaceStructure).
# `restrict_to` = persona ids the shortcut is limited to; empty tuple = inherit the workspace's
# visibility (anyone who can see the workspace sees the shortcut).
SHORTCUTS = {
	"site-execution": [
		{"label": "Projects", "icon": "📋", "route": "/projects", "sort": 1, "restrict_to": ()},
		{"label": "Tasks", "icon": "✓", "route": "/tasks", "sort": 3, "restrict_to": ()},
		{
			"label": "Progress Entries", "icon": "📝", "route": "/progress-entries", "sort": 5,
			"restrict_to": ("admin", "bsa", "director", "pm", "site-engineer", "foreman"),
		},
		{"label": "Scope Change Orders", "icon": "🔁", "route": "/sco", "sort": 6, "restrict_to": ()},
		{"label": "Schedule", "icon": "📅", "route": "/schedule", "sort": 7, "restrict_to": ()},
	],
}


def seed_workspace_shortcuts():
	"""Upsert the seeded shortcut tiles (idempotent, keyed on workspace + label). Only creates
	the seed set; admin edits/additions via the Workspace Structure screen are preserved."""
	if not frappe.db.exists("DocType", "BuildSuite Workspace Shortcut"):
		return

	for workspace, shortcuts in SHORTCUTS.items():
		if not frappe.db.exists("BuildSuite Workspace", workspace):
			continue
		for sc in shortcuts:
			roles = [
				{"role": PERSONA_ROLE[p]} for p in sc["restrict_to"] if frappe.db.exists("Role", PERSONA_ROLE[p])
			]
			name = frappe.db.get_value(
				"BuildSuite Workspace Shortcut", {"workspace": workspace, "label": sc["label"]}
			)
			doc = (
				frappe.get_doc("BuildSuite Workspace Shortcut", name)
				if name
				else frappe.new_doc("BuildSuite Workspace Shortcut")
			)
			doc.workspace = workspace
			doc.label = sc["label"]
			doc.icon = sc["icon"]
			doc.route = sc["route"]
			doc.sort_order = sc["sort"]
			doc.enabled = 1
			doc.set("roles", roles)
			doc.save(ignore_permissions=True)
