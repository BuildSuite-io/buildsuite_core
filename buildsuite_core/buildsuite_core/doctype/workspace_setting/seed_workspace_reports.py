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


def _pf_gl_route(company, account=None, group_by_account=False):
	"""A General Ledger Desk route, scoped to the company and (optionally) one account or grouped
	by account, so the tile opens to something useful instead of a blank GL prompt."""
	from urllib.parse import quote

	parts = []
	if company:
		parts.append(f"company={quote(company)}")
	if account:
		parts.append(f"account={quote(account)}")
	if group_by_account:
		parts.append(f"group_by={quote('Group by Account')}")
	base = "/app/query-report/General Ledger"
	return base + ("?" + "&".join(parts) if parts else "")


def _project_finance_tiles():
	"""Project Finance tiles, computed per-site. Receivables & Payables and Financial Position
	are bespoke in-app Vue views (real data, prototype layout). Profit & Loss / Petty Cash /
	Expense Summary / Cash & Bank ride ERPNext Desk reports, pre-filtered to this site's company
	and the relevant account so they open populated (a bare General Ledger needs a mandatory
	account and lands blank)."""
	from urllib.parse import quote

	from buildsuite_core.utils.project import default_company

	company = default_company()

	def _first_account(account_type, contains=None):
		names = (
			frappe.get_all(
				"Account",
				filters={"company": company, "account_type": account_type, "is_group": 0},
				pluck="name",
			)
			if company
			else []
		)
		if contains:
			names = [n for n in names if contains in n]
		return names[0] if names else None

	petty = _first_account("Cash", contains="Petty")
	bank = _first_account("Bank")
	pnl_route = "/app/query-report/Profit and Loss Statement" + (
		f"?company={quote(company)}" if company else ""
	)
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
			"route": _pf_gl_route(company, account=petty),
			"description": "Petty cash ledger — the Petty Cash account, per holder.",
		},
		{
			"label": "Expense Summary",
			"icon": "receipt",
			"route": _pf_gl_route(company, group_by_account=True),
			"description": "Ledger grouped by account — read the expense accounts.",
		},
		{
			"label": "Cash & Bank Statement",
			"icon": "banknote",
			"route": _pf_gl_route(company, account=bank),
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

	# Project Finance — computed per-site (bespoke in-app views + pre-filtered ERPNext reports).
	if "project-finance" not in existing:
		for row in _project_finance_tiles():
			settings.append("reports", {"workspace": "project-finance", **row})
		changed = True

	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
