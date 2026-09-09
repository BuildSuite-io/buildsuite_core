# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Workforce workspace's report tiles were hardcoded in the SPA landing view while every other
workspace draws its tiles from Workspace Setting. Workforce has now joined the WORKSPACES allowlist
and its tiles (Labour Attendance Register, Overtime Attendance Register, Site Attendance Summary)
are seeded like the rest. The workspace seeder is install-only, so this patch seeds the workforce
tiles on already-provisioned sites. Idempotent — it no-ops if any workforce row already exists."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import _SEED


def execute():
	settings = frappe.get_single("Workspace Setting")
	if any(r.workspace == "workforce" for r in settings.reports):
		return
	for row in _SEED["workforce"]:
		settings.append("reports", {"workspace": "workforce", **row})
	settings.flags.ignore_permissions = True
	settings.save()
