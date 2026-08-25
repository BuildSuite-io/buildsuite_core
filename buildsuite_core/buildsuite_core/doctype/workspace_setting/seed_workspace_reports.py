# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the per-workspace report-style shortcut tiles (Workspace Setting Single).

Seeds each live workspace's `reports` rows: Site Execution, Subcontract and Procurement.
Idempotent per workspace — a workspace that already has rows is left untouched (respects
admin edits).

Billing and Collection, Subcontractor Position and Material Status are standard Script Reports
(buildsuite_core/report/<slug>/) synced from files — crash-safe on the empty-filter run Frappe
fires on page load (a Query Report's %(x)s substitution would blow up there), and able to return
summary cards. Their roles and filters live in each report's own definition; this module only
drives the workspace tile. Delay Analysis is a bespoke in-app view, tiled as a plain route."""

import frappe

# Delay Analysis is served by a bespoke in-app view (not the flat report renderer), so its
# workspace tile points at this route rather than referencing a Report.
DELAY_ANALYSIS_ROUTE = "/reports/delay-analysis"

# Site Execution report tiles: (report_name_or_label, icon, description). Delay Analysis is a
# route tile; the other three reference their Script Reports by name.
REPORTS = (
	("Delay Analysis", "calendar", "Stages slipping, by how much, and current progress."),
	("Billing and Collection", "banknote", "Invoiced, received, overdue and retention held, per project."),
	(
		"Subcontractor Position",
		"subcontract",
		"WO value, measured, billed, paid, retention and outstanding, per subcontractor.",
	),
	("Material Status", "package", "Ordered → received → consumed → at site, by item."),
)


# Former hardcoded workspace tiles (functional ones only — the "coming soon" placeholder
# tiles had no destination and are dropped). Seeded as explicit routes / report references.
_SEED = {
	"subcontract": (
		{
			"label": "Work Order Register",
			"icon": "clipboard-list",
			"report": "Subcontractor Work Order Register",
			"description": "Every WO across projects with status + billed-to-date.",
		},
		{
			"label": "Measurement Book Register",
			"icon": "chart-bar",
			"report": "Measurement Book Register",
			"description": "Site measurements certified by the QS, feeding subcontractor bill qty.",
		},
		{
			"label": "Subcontractor Bill Register",
			"icon": "file-text",
			"report": "Subcontractor Bill Register",
			"description": "Running subcontractor bills with retention + net payable rollups.",
		},
	),
	"procurement": (
		{
			"label": "Requests waiting to be ordered",
			"icon": "clipboard-list",
			"route": "/procurement/report/requests-to-order",
			"description": "Asked for by site, not yet on an order.",
		},
		{
			"label": "Delivery follow-up",
			"icon": "chart-line",
			"route": "/procurement/report/delivery-followup",
			"description": "Open orders by the date they were needed, and what is late.",
		},
		{
			"label": "Material at site",
			"icon": "package",
			"route": "/procurement/report/site-stock",
			"description": "Received minus consumed, per item, at each project store.",
		},
		{
			"label": "Purchase rate vs estimate",
			"icon": "chart-bar",
			"route": "/procurement/report/rate-check",
			"description": "What you are paying against the QS rate in the Rate Master.",
		},
		{
			"label": "Purchase register",
			"icon": "file-text",
			"route": "/procurement/report/purchase-register",
			"description": "Every order line — supplier, item, quantity, rate.",
		},
		{
			"label": "Consumption by cost code",
			"icon": "hard-hat",
			"route": "/procurement/report/consumption-by-cost-code",
			"description": "Material issued to site, against the cost code it was booked to.",
		},
	),
}


def _project_finance_tiles():
	"""Project Finance tiles — all six are bespoke in-app Vue views (real data via
	api.finance_report / api.expense_entry, prototype layout). Profit & Loss is now our own
	account-tree P&L (api.finance_report.profit_and_loss), not the stock ERPNext report, so the
	whole workspace uses our variant; its own filter bar carries project + period."""
	return (
		{
			"label": "Profit & Loss",
			"icon": "chart-line",
			"route": "/project-finance/report/pnl",
			"description": "Income vs direct costs and overheads, by project and period.",
		},
		{
			"label": "Receivables & Payables",
			"icon": "clipboard-list",
			"route": "/project-finance/report/aged",
			"description": "Aged outstanding — who owes us and who we owe.",
		},
		{
			"label": "Financial Position",
			"icon": "wallet",
			"route": "/project-finance/report/position",
			"description": "What we have vs what we owe, and the net position.",
		},
		{
			"label": "Petty Cash",
			"icon": "hand-coins",
			"route": "/project-finance/report/petty",
			"description": "Petty cash ledger — the Petty Cash account, per holder.",
		},
		{
			"label": "Expense Summary",
			"icon": "receipt",
			"route": "/project-finance/report/expenses",
			"description": "Submitted expenses grouped by project, account, cost code, source or person.",
		},
		{
			"label": "Cash & Bank Statement",
			"icon": "banknote",
			"route": "/project-finance/report/cashbank",
			"description": "Per account: opening, movements, closing.",
		},
	)


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

	# Site Execution — prefer migrated admin config, else the default report set. Delay
	# Analysis is a bespoke in-app view, tiled as a plain route; the rest reference Reports.
	if "site-execution" not in existing:
		legacy = _legacy_site_execution_rows()
		rows = legacy or [
			{"label": name, "route": DELAY_ANALYSIS_ROUTE, "icon": icon, "description": desc}
			if name == "Delay Analysis"
			else {"report": name, "icon": icon, "description": desc}
			for name, icon, desc in REPORTS
		]
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

	# Project Finance — computed per-site (bespoke in-app views + the pre-filtered ERPNext P&L).
	if "project-finance" not in existing:
		for row in _project_finance_tiles():
			settings.append("reports", {"workspace": "project-finance", **row})
		changed = True

	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
