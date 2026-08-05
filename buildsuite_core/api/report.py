# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Run a Frappe/ERPNext Report (Query or Script) and return its columns + rows, so the Vue
app can render any report in-app instead of bouncing to the Desk. A thin, permission-checked
wrapper over frappe.desk.query_report.run — the generic FrappeReport component consumes it."""

import frappe
from frappe import _
from frappe.utils import nowdate


def _resolve_default(fieldtype, default):
	"""Resolve a report filter's stored default. Handles the common tokens Frappe uses
	(Today for dates, the user's default Company) and leaves plain literals as-is."""
	default = (default or "").strip()
	if not default:
		return ""
	if fieldtype in ("Date", "Datetime") and default.lower() in ("today", "now"):
		return nowdate()
	if default.lower() in ("company", "user_default:company"):
		return frappe.defaults.get_user_default("Company") or ""
	# Ignore JS/expression defaults (frappe.*, () => …) — the UI seeds them empty.
	if default.startswith("frappe.") or "=>" in default or "(" in default:
		return ""
	return default


@frappe.whitelist()
def get_report_filters(report):
	"""Everything the in-app renderer needs to build a report's filter bar agnostically:

	- `script`: the report's client script (as Frappe's Desk loads it). The renderer evals
	  it in a small frappe shim to read the report's DYNAMIC filters (frappe.query_reports
	  [name].filters), including their computed defaults — so ANY Frappe/ERPNext report's
	  filters are exposed, not just BuildSuite's.
	- `filters`: the Report Filter child table (Frappe's JS-free filter source), used as the
	  fallback when a report defines no script filters — mirroring query_report.js.
	"""
	doc = frappe.get_cached_doc("Report", report)
	if not doc.is_permitted():
		frappe.throw(_("You don't have access to Report: {0}").format(report), frappe.PermissionError)

	child = [
		{
			"fieldname": f.fieldname,
			"label": f.label or f.fieldname,
			"fieldtype": f.fieldtype,
			"options": f.options,
			"mandatory": int(f.mandatory or 0),
			"default": _resolve_default(f.fieldtype, f.default),
		}
		for f in (doc.filters or [])
		if f.fieldname and f.fieldtype not in ("Fold", "Column Break", "Section Break")
	]

	script = ""
	try:
		from frappe.desk.query_report import get_script

		script = (get_script(report) or {}).get("script") or ""
	except Exception:
		script = ""

	return {"script": script, "filters": child}


@frappe.whitelist()
def run_report(report, filters=None):
	"""Execute a Query/Script Report and return {report_name, ref_doctype, columns, result}.
	`frappe.desk.query_report.run` enforces the report's own read permission."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters) or {}
	filters = filters or {}

	meta = frappe.db.get_value(
		"Report", report, ["report_name", "report_type", "ref_doctype", "disabled"], as_dict=True
	)
	if not meta:
		frappe.throw(_("Report {0} not found.").format(report))
	if meta.disabled:
		frappe.throw(_("Report {0} is disabled.").format(report))

	from frappe.desk.query_report import run

	res = run(report, filters=filters, ignore_prepared_report=True) or {}
	return {
		"report_name": meta.report_name or report,
		"report_type": meta.report_type,
		"ref_doctype": meta.ref_doctype,
		"columns": res.get("columns") or [],
		"result": res.get("result") or [],
		"message": res.get("message"),
	}
