# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Project Finance report tiles were reworked several times. This early patch originally
synced two bespoke Script Reports (receivables_and_payables / financial_position) and repointed
the tiles from a static _SEED["project-finance"] list. Both are gone now: those reports became
in-app Vue views, and the tile set moved to _project_finance_tiles(). A site that migrates for
the first time after those changes hit `KeyError: 'project-finance'` here, which aborted the whole
migration. Repoint the Project Finance tiles from the current source instead — the later PF
patches rebuild the same set idempotently, so this stays consistent with them."""

import frappe

from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
	_project_finance_tiles,
)


def execute():
	# Repoint only the project-finance tiles; leave the other workspaces' rows untouched.
	settings = frappe.get_single("Workspace Setting")
	kept = [
		{
			"workspace": r.workspace,
			"label": r.label,
			"report": r.report,
			"route": r.route,
			"icon": r.icon,
			"description": r.description,
		}
		for r in settings.reports
		if r.workspace != "project-finance"
	]
	settings.set("reports", [])
	for row in kept:
		settings.append("reports", row)
	for row in _project_finance_tiles():
		settings.append("reports", {"workspace": "project-finance", **row})
	settings.flags.ignore_permissions = True
	settings.save()
