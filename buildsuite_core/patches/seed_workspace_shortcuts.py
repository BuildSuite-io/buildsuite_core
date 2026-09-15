"""Seed the BuildSuite Workspace Shortcut registry on existing/imported sites.

The registry gained per-workspace quick-nav shortcuts (formerly the client-side
seed.js workspaceStructure). seed_workspace_shortcuts() is idempotent; this runs it once
for sites that predate the shortcut doctype. The schema is created by migrate before
patches run; the workspaces themselves were seeded by seed_workspace_registry.
"""

import frappe


def execute():
	from buildsuite_core.buildsuite_core.doctype.buildsuite_workspace.seed_workspaces import (
		seed_workspace_shortcuts,
	)

	seed_workspace_shortcuts()
	frappe.db.commit()
	frappe.clear_cache()
	print("seed_workspace_shortcuts: seeded the BuildSuite Workspace Shortcut registry")
