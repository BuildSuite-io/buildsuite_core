"""Seed the BuildSuite Workspace registry on existing/imported sites.

The registry (BuildSuite Workspace + its Visible-To roles) is the backend source for SPA
sidebar visibility + ordering, replacing the frontend WORKSPACE_VISIBILITY / WORKSPACE_ORDER
matrices. seed_workspaces() is idempotent; this runs it once for sites that predate the
registry. The doctype schema itself is created by migrate before patches run.
"""

import frappe


def execute():
	from buildsuite_core.buildsuite_core.doctype.buildsuite_workspace.seed_workspaces import (
		seed_workspaces,
	)

	seed_workspaces()
	frappe.clear_cache()
	print("seed_workspace_registry: seeded the BuildSuite Workspace registry")
