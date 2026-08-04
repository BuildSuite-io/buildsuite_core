# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Run a Frappe/ERPNext Report (Query or Script) and return its columns + rows, so the Vue
app can render any report in-app instead of bouncing to the Desk. A thin, permission-checked
wrapper over frappe.desk.query_report.run — the generic FrappeReport component consumes it."""

import frappe
from frappe import _


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
