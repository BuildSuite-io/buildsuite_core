# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Workforce landing gained a Timesheets record tile (as in the prototype). The workspace
seeder is install-only, so this seeds it on already-provisioned sites. Idempotent — it no-ops if
the workforce workspace already has any record tile (an admin may have curated them)."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	DOCTYPE_SEED,
)


def execute():
	settings = frappe.get_single("Workspace Setting")
	if any(r.workspace == "workforce" for r in settings.doctypes):
		return
	for row in DOCTYPE_SEED["workforce"]:
		settings.append("doctypes", {"workspace": "workforce", **row})
	settings.flags.ignore_permissions = True
	settings.save()
