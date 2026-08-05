# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Re-sync the Site Execution Query Reports so existing sites pick up the
	filter-aware SQL + Report Filter rows (project / date range). seed_workspace_reports
	now upserts each report's query + filters; workspace tiles are left untouched.
	Idempotent."""
	from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
		seed_workspace_reports,
	)

	seed_workspace_reports()
	frappe.db.commit()  # nosemgrep
