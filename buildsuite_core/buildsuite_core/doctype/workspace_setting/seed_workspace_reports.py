# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the per-workspace report-style shortcut tiles (Workspace Setting Single).

Seeds each live workspace's `reports` rows: Site Execution (the four standard Script Reports
in buildsuite_core/report/, or migrated from the legacy Site Execution Settings when present),
Subcontract + Procurement from their former hardcoded tiles. Idempotent per workspace — a
workspace that already has rows is left untouched (respects admin edits)."""

import frappe

# The four Site Execution report tiles → their standard Script Reports (in
# buildsuite_core/buildsuite_core/report/<slug>/). Script Reports, NOT Query Reports, so each
# builds its SQL binding filters only when set — Frappe fires an initial run with empty filters
# on page load, which would crash a Query Report's %(x)s substitution. The report's roles and
# filters live in its own definition; this tuple only drives the workspace tile.
REPORTS = (
	("Delay Analysis", "calendar", "Stages slipping, by how much, and current progress."),
	(
		"Billing and Collection",
		"banknote",
		"Invoiced, received, overdue and retention held, per project.",
	),
	(
		"Subcontractor Position",
		"subcontract",
		"WO value, measured, billed, paid, retention and outstanding, per subcontractor.",
	),
	("Material Status", "package", "Ordered → received → consumed → at site, by item."),
)


# Former hardcoded workspace tiles (functional ones only — the "coming soon" placeholder
# tiles had no destination and are dropped). Seeded as explicit routes.
_SEED = {
	"subcontract": (
		{
			"label": "Work Order Register",
			"icon": "clipboard-list",
			"route": "/subcontractor-work-orders",
			"description": "Every WO across projects with status + committed value.",
		},
		{
			"label": "Measurement Book Register",
			"icon": "chart-bar",
			"route": "/measurement-books",
			"description": "Site measurements certified by the QS, feeding billed quantity.",
		},
	),
	"procurement": (
		{
			"label": "Stock Balance",
			"icon": "chart-bar",
			"route": "/app/query-report/Stock Balance",
			"description": "Item-wise on-hand quantity across warehouses.",
		},
		{
			"label": "Stock Ledger",
			"icon": "file-text",
			"route": "/app/query-report/Stock Ledger",
			"description": "Every stock movement — receipts, issues, transfers.",
		},
		{
			"label": "Item-wise Purchase Register",
			"icon": "clipboard-list",
			"route": "/app/query-report/Item-wise Purchase Register",
			"description": "POs and GRNs grouped by item, with value rollups.",
		},
	),
}


def _legacy_site_execution_rows():
	"""Admin-edited reports on the deprecated Site Execution Settings Single, if it's
	still around (migration path). Read via raw SQL — the old controller module is gone,
	so frappe.get_single would fail to import it. Empty on a fresh install."""
	if not frappe.db.table_exists("Site Execution Report"):
		return []
	rows = frappe.db.sql(
		"""SELECT report, icon, description FROM `tabSite Execution Report`
		   WHERE parenttype = 'Site Execution Settings' ORDER BY idx""",
		as_dict=True,
	)
	return [
		{"report": r.report, "icon": r.icon or "file-text", "description": r.description or ""}
		for r in rows
		if r.report
	]


def seed_workspace_reports():
	settings = frappe.get_single("Workspace Setting")
	existing = {r.workspace for r in settings.reports}
	changed = False

	# Site Execution — prefer migrated admin config, else the default report set.
	if "site-execution" not in existing:
		legacy = _legacy_site_execution_rows()
		rows = legacy or [{"report": name, "icon": icon, "description": desc} for name, icon, desc in REPORTS]
		for r in rows:
			settings.append("reports", {"workspace": "site-execution", **r})
		changed = True

	# Subcontract + Procurement — their former hardcoded tiles.
	for slug, rows in _SEED.items():
		if slug in existing:
			continue
		for row in rows:
			settings.append("reports", {"workspace": slug, **row})
		changed = True

	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
