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


def _project_finance_tiles():
	"""Project Finance tiles, computed per-site. Receivables & Payables, Financial Position,
	Petty Cash, Expense Summary and Cash & Bank are all bespoke in-app Vue views (real data,
	prototype layout). Only Profit & Loss stays an ERPNext report, shown through the IN-APP
	renderer pre-filled with this site's company and a rolling last-12-months period so it opens
	populated; the in-app filter bar lets a user change the dates."""
	from urllib.parse import quote

	from frappe.utils import add_years, nowdate

	from buildsuite_core.utils.project import default_company

	company = default_company()
	to_date = nowdate()
	from_date = add_years(to_date, -1)

	pnl_parts = []
	if company:
		pnl_parts.append(f"company={quote(company)}")
	pnl_parts += [
		f"filter_based_on={quote('Date Range')}",
		f"period_start_date={from_date}",
		f"period_end_date={to_date}",
		"periodicity=Yearly",
	]
	pnl_route = "/reports/view/" + quote("Profit and Loss Statement") + "?" + "&".join(pnl_parts)
	return (
		{
			"label": "Profit & Loss",
			"icon": "chart-line",
			"route": pnl_route,
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
