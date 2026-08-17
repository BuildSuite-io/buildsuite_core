# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the per-workspace report-style shortcut tiles (Workspace Setting Single).

Creates the Site Execution Query Reports (as before), then seeds each live workspace's
`reports` rows: Site Execution from those reports (or migrated from the legacy Site
Execution Settings when present), Subcontract + Procurement from their former hardcoded
tiles. Idempotent per workspace — a workspace that already has rows is left untouched
(respects admin edits)."""

import frappe

# Delay Analysis is served by a bespoke in-app view (not the flat Query Report renderer), so
# its workspace tile points at this route rather than referencing the Report.
DELAY_ANALYSIS_ROUTE = "/reports/delay-analysis"

# Reusable Report Filter rows (Frappe's server-side filter defs the in-app FrappeReport
# renderer reads). A Query Report's SQL uses them via %(fieldname)s; the "empty ⇒ all"
# guard (%(x)s = '' OR …) keeps every filter optional.
_PROJECT = {"fieldname": "project", "label": "Project", "fieldtype": "Link", "options": "Project"}
_FROM = {"fieldname": "from_date", "label": "From", "fieldtype": "Date"}
_TO = {"fieldname": "to_date", "label": "To", "fieldtype": "Date"}

# Role sets for the Site Execution reports (who may RUN each). Restricted reports are
# also hidden as tiles for users who can't run them — see workspace_setting._resolve.
_SITE_ROLES = (
	"System Manager",
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite QS",
	"BuildSuite Site Engineer",
	"BuildSuite Foreman",
)
_FINANCE_ROLES = (
	"System Manager",
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite QS",
	"BuildSuite Accountant",
)

# --- SQL for the four Site Execution reports. Query Reports: columns are declared inline
#     as `field AS "Label:Type:Width"`; filters are optional via the `%(x)s = '' OR …` guard. ---

_DELAY_SQL = """
SELECT name AS "Stage:Link/Stage Planning:200", stage_name AS "Stage Name:Data:180",
	project AS "Project:Link/Project:180", planned_end AS "Planned End:Date:110",
	mean_progress AS "Progress:Percent:100", DATEDIFF(CURDATE(), planned_end) AS "Days Late:Int:90"
FROM `tabStage Planning`
WHERE planned_end IS NOT NULL AND planned_end < CURDATE() AND IFNULL(mean_progress, 0) < 100
	AND (%(project)s = '' OR project = %(project)s)
ORDER BY DATEDIFF(CURDATE(), planned_end) DESC
"""

_BILLING_SQL = """
SELECT si.project AS "Project:Link/Project:200",
	SUM(si.grand_total) AS "Invoiced:Currency:120",
	SUM(si.grand_total - si.outstanding_amount) AS "Received:Currency:120",
	SUM(si.outstanding_amount) AS "Outstanding:Currency:120",
	SUM(CASE WHEN si.due_date < CURDATE() THEN si.outstanding_amount ELSE 0 END) AS "Overdue:Currency:120",
	(SELECT IFNULL(SUM(sb.retention_amount), 0) FROM `tabSubcontractor Bill` sb
		WHERE sb.docstatus = 1 AND sb.project = si.project) AS "Retention Held:Currency:130"
FROM `tabSales Invoice` si
WHERE si.docstatus = 1 AND si.project IS NOT NULL AND si.project <> ''
	AND (%(project)s = '' OR si.project = %(project)s)
	AND (%(from_date)s = '' OR si.posting_date >= %(from_date)s)
	AND (%(to_date)s = '' OR si.posting_date <= %(to_date)s)
GROUP BY si.project ORDER BY SUM(si.outstanding_amount) DESC
"""

_SUBPOS_SQL = """
SELECT subcontractor AS "Subcontractor:Link/Supplier:200", MAX(subcontractor_name) AS "Name:Data:200",
	SUM(wo_value) AS "WO Value:Currency:110", SUM(measured) AS "Measured Qty:Float:110",
	SUM(billed) AS "Billed:Currency:110", SUM(retention) AS "Retention:Currency:110",
	SUM(paid) AS "Paid:Currency:110", SUM(billed) - SUM(paid) AS "Outstanding:Currency:110"
FROM (
	SELECT wo.subcontractor, wo.subcontractor_name, wo.total_value AS wo_value, 0 measured, 0 billed, 0 retention, 0 paid
		FROM `tabSubcontractor Work Order` wo WHERE wo.docstatus = 1 AND (%(project)s = '' OR wo.project = %(project)s)
	UNION ALL
	SELECT wo.subcontractor, wo.subcontractor_name, 0, mb.measured_total, 0, 0, 0
		FROM `tabMeasurement Book` mb JOIN `tabSubcontractor Work Order` wo ON wo.name = mb.work_order
		WHERE mb.status = 'Certified' AND (%(project)s = '' OR mb.project = %(project)s)
	UNION ALL
	SELECT sb.subcontractor, sb.subcontractor_name, 0, 0, sb.gross, sb.retention_amount,
		IFNULL((SELECT pi.grand_total - pi.outstanding_amount FROM `tabPurchase Invoice` pi WHERE pi.name = sb.purchase_invoice), 0)
		FROM `tabSubcontractor Bill` sb WHERE sb.docstatus = 1 AND (%(project)s = '' OR sb.project = %(project)s)
) x
GROUP BY subcontractor HAVING SUM(wo_value) + SUM(billed) > 0 ORDER BY SUM(wo_value) DESC
"""

_MATERIAL_SQL = """
SELECT item_code AS "Item:Link/Item:220",
	SUM(ordered) AS "Ordered:Float:110", SUM(received) AS "Received:Float:110",
	SUM(consumed) AS "Consumed:Float:110", SUM(received) - SUM(consumed) AS "At Site:Float:110"
FROM (
	SELECT poi.item_code, poi.qty AS ordered, 0 received, 0 consumed
		FROM `tabPurchase Order Item` poi JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE po.docstatus = 1 AND (%(project)s = '' OR poi.project = %(project)s)
	UNION ALL
	SELECT pri.item_code, 0, pri.received_qty, 0
		FROM `tabPurchase Receipt Item` pri JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pr.docstatus = 1 AND (%(project)s = '' OR pri.project = %(project)s)
	UNION ALL
	SELECT sed.item_code, 0, 0, sed.qty
		FROM `tabStock Entry Detail` sed JOIN `tabStock Entry` se ON se.name = sed.parent
		WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Issue' AND (%(project)s = '' OR se.project = %(project)s)
) x
GROUP BY item_code HAVING SUM(ordered) + SUM(received) + SUM(consumed) > 0 ORDER BY item_code
"""

# (report_name, ref_doctype, icon, description, query, filters, roles) — the Site Execution
# reports, reworked to match the prototype's Overview report set.
REPORTS = (
	(
		"Delay Analysis",
		"Stage Planning",
		"calendar",
		"Stages slipping, by how much, and current progress.",
		_DELAY_SQL,
		(_PROJECT,),
		_SITE_ROLES,
	),
	(
		"Billing and Collection",
		"Sales Invoice",
		"banknote",
		"Invoiced, received, overdue and retention held, per project.",
		_BILLING_SQL,
		(_PROJECT, _FROM, _TO),
		_FINANCE_ROLES,
	),
	(
		"Subcontractor Position",
		"Subcontractor Work Order",
		"subcontract",
		"WO value, measured, billed, paid, retention and outstanding, per subcontractor.",
		_SUBPOS_SQL,
		(_PROJECT,),
		_FINANCE_ROLES,
	),
	(
		"Material Status",
		"Item",
		"package",
		"Ordered → received → consumed → at site, by item.",
		_MATERIAL_SQL,
		(_PROJECT,),
		_SITE_ROLES,
	),
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


def _ensure_report(report_name, ref_doctype, query, filters=(), roles=()):
	"""Create the report, or sync its query, filter defs AND roles if it already exists (so
	updated queries / role restrictions reach sites seeded earlier). Returns True on create."""
	existing = frappe.db.exists("Report", report_name)
	if existing:
		doc = frappe.get_doc("Report", report_name)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Report",
				"report_name": report_name,
				"ref_doctype": ref_doctype,
				"report_type": "Query Report",
				"is_standard": "No",
				"module": "BuildSuite Core",
			}
		)

	# Reconcile the roles that may run this report (drives both execution and, via
	# workspace_setting._resolve, whether the tile is shown to a user).
	doc.set("roles", [])
	for role in roles:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})

	doc.query = query
	doc.set("filters", [])
	for f in filters:
		doc.append(
			"filters",
			{
				"fieldname": f["fieldname"],
				"label": f["label"],
				"fieldtype": f["fieldtype"],
				"options": f.get("options", ""),
				"mandatory": f.get("mandatory", 0),
				"default": f.get("default", ""),
			},
		)
	doc.flags.ignore_permissions = True
	doc.save()
	return not existing


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
	created = []
	for report_name, ref_doctype, _icon, _desc, query, filters, roles in REPORTS:
		if _ensure_report(report_name, ref_doctype, query, filters, roles):
			created.append(report_name)

	settings = frappe.get_single("Workspace Setting")
	existing = {r.workspace for r in settings.reports}
	changed = False

	# Site Execution — prefer migrated admin config, else the default report set.
	if "site-execution" not in existing:
		legacy = _legacy_site_execution_rows()
		# Delay Analysis is a bespoke in-app view, not a flat Query Report — tile it as a plain
		# route so the Workspace Setting reads clearly (a URL, not a report reference).
		rows = legacy or [
			{"label": name, "route": DELAY_ANALYSIS_ROUTE, "icon": icon, "description": desc}
			if name == "Delay Analysis"
			else {"report": name, "icon": icon, "description": desc}
			for name, _ref, icon, desc, _q, _f, _r in REPORTS
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

	if changed:
		settings.flags.ignore_permissions = True
		settings.save()
	return created
