# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Retire the Site Execution Settings Single (+ its Site Execution Report child) in
favour of the generalized Workspace Setting. Migrates any admin-edited reports into the
'site-execution' workspace, then drops the old doctypes."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Site Execution Settings"):
		return

	# Ensure the new doctypes are synced this migrate before we read/write them.
	frappe.reload_doc("buildsuite_core", "doctype", "workspace_report")
	frappe.reload_doc("buildsuite_core", "doctype", "workspace_setting")

	# Migrate legacy reports + seed the workspace tiles (idempotent).
	from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
		seed_workspace_reports,
	)

	seed_workspace_reports()

	# Drop the old Single + its child doctype.
	for doctype in ("Site Execution Settings", "Site Execution Report"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
