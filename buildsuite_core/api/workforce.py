# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Workforce dashboard — workers, crews, man-days and labour cost at a glance.

Every read goes through get_list / get_all with the caller's permissions, so a user sees only the
sites (project team scope) and companies they may read."""

import frappe
from frappe.utils import flt

from buildsuite_core.utils.project import company_scope

LABOUR_REGISTER = "Labour Attendance Register"
OVERTIME_REGISTER = "Overtime Attendance Register"
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


def _labour_totals() -> dict:
	"""Man-days and labour cost from the SUBMITTED registers (both are derived from submitted Field
	Attendance, so a draft sheet is in neither). A half day counts as half a man-day; labour cost is
	wages plus overtime wages."""
	labour = frappe.get_list(
		LABOUR_REGISTER,
		filters=_scoped({"docstatus": 1}),
		fields=["status", "daily_wage_calculated"],
		limit_page_length=0,
	)
	overtime = frappe.get_list(
		OVERTIME_REGISTER,
		filters=_scoped({"docstatus": 1}),
		fields=["overtime_wage_calculated"],
		limit_page_length=0,
	)
	man_days = sum({"Full Day": 1, "Half Day": 0.5}.get(r.status, 0) for r in labour)
	cost = sum(flt(r.daily_wage_calculated) for r in labour) + sum(
		flt(r.overtime_wage_calculated) for r in overtime
	)
	return {"man_days": round(man_days, 1), "labour_cost": cost}


def _recent_attendance() -> list[dict]:
	return frappe.get_list(
		FIELD_ATTENDANCE,
		filters=_scoped({"docstatus": ["<", 2]}),
		fields=["name", "project", "project_name", "date", "docstatus", "employees_count"],
		order_by="date desc, creation desc",
		limit=6,
	)


def _recent_labour() -> list[dict]:
	return frappe.get_list(
		LABOUR_REGISTER,
		filters=_scoped({"docstatus": 1}),
		fields=[
			"name",
			"employee_name",
			"daily_wage_calculated",
			"project",
			"project_name",
			"cost_code_label",
			"attendance_date",
			"status",
		],
		order_by="attendance_date desc, creation desc",
		limit=6,
	)
