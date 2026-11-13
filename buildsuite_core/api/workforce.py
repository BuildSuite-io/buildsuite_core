# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Workforce dashboard — workers, crews, man-days and labour cost at a glance.

Every read goes through get_list / get_all with the caller's permissions, so a user sees only the
sites (project team scope) and companies they may read."""

import frappe

from buildsuite_core.utils.labour_cost import labour_cost_rows, totals
from buildsuite_core.utils.project import company_scope

LABOUR_REGISTER = "Labour Attendance Register"
FIELD_ATTENDANCE = "Field Attendance"


def _scoped(extra: dict | None = None) -> dict:
	"""Filters limited to the working company when company awareness is on."""
	scope = company_scope()
	return {**({"company": scope} if scope else {}), **(extra or {})}


@frappe.whitelist()
def get_dashboard() -> dict:
	return {
		"active_workers": len(
			frappe.get_list(
				"Employee", filters={"is_labour": 1, "status": "Active", **_scoped()}, pluck="name"
			)
		),
		"active_crews": len(frappe.get_list("Crew", filters=_scoped(), pluck="name")),
		**_labour_totals(),
		"recent_attendance": _recent_attendance(),
		"recent_labour": _recent_labour(),
	}


def _readable_rows() -> list[dict]:
	"""Labour register rows (attendance and timesheets alike) on the projects this user can read, in
	the working company: the one reader, utils.labour_cost, narrowed by the project permissions."""
	projects = frappe.get_list("Project", filters=_scoped(), pluck="name", limit_page_length=0)
	return labour_cost_rows({"projects": projects})


def _labour_totals() -> dict:
	"""Man-days and labour cost from the submitted registers, both captured as attendance and as
	timesheets. Man-days are hours over the full day each row was made with, never counted from the
	status; labour cost is wages plus overtime wages."""
	t = totals(_readable_rows())
	return {"man_days": round(t["man_days"], 1), "labour_cost": t["cost"]}


def _recent_attendance() -> list[dict]:
	return frappe.get_list(
		FIELD_ATTENDANCE,
		filters=_scoped({"docstatus": ["<", 2]}),
		fields=["name", "project", "project_name", "date", "docstatus", "employees_count"],
		order_by="date desc, creation desc",
		limit=6,
	)


def _recent_labour() -> list[dict]:
	"""The latest regular (non-overtime) register rows, whether captured as attendance or timesheet."""
	rows = [r for r in _readable_rows() if r["doctype"] == LABOUR_REGISTER]
	rows.sort(key=lambda r: (str(r["date"] or ""), r["name"]), reverse=True)
	names = {
		p.name: p.project_name
		for p in frappe.get_all(
			"Project",
			filters={"name": ["in", list({r["project"] for r in rows[:6]}) or [""]]},
			fields=["name", "project_name"],
		)
	}
	return [
		{
			"name": r["name"],
			"employee_name": r["employee_name"],
			"daily_wage_calculated": r["regular_cost"],
			"project": r["project"],
			"project_name": names.get(r["project"]) or r["project"],
			"cost_code_label": (r["cost_code"] or {}).get("label") or "",
			"attendance_date": str(r["date"]) if r["date"] else None,
			"status": r["status"],
			"source": r["source"],
		}
		for r in rows[:6]
	]
