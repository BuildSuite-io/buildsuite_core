# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The one reading of labour cost.

Labour is recorded twice over: a submitted Field Attendance sheet and a submitted Timesheet each
create rows in the Labour and Overtime Attendance Registers. Everything that costs or counts labour -
the BOQ Actual, the dashboards, the project cost heads - reads the registers through
`labour_cost_rows`, and none of them may also read Timesheet or Field Attendance directly: both are
already in the registers, so a second read counts the same hours twice."""

import frappe
from frappe.utils import flt, getdate

LABOUR = "Labour Attendance Register"
OVERTIME = "Overtime Attendance Register"


def labour_cost_rows(filters: dict | None = None) -> list[dict]:
	"""Every submitted register row whose parent (the Field Attendance sheet or the Timesheet) is also
	submitted, one output row per register row.

	filters (all optional): project, projects (a list / set), worker (employee), from, to, source
	("Attendance" | "Timesheet").

	Each row: doctype, name, source, employee, employee_name, project, date, task, status,
	field_attendance, timesheet, description, cost_code ({type, group_code, item_code, label} or
	None: the row's own, else its sheet's), and
	  regular_hours, full_day_hours, man_days (regular_hours / full_day_hours - never from the status),
	  regular_cost,
	  ot_hours, ot_cost.
	A Labour register row carries the regular side, an Overtime row the overtime side."""
	filters = filters or {}
	out = []
	for doctype in (LABOUR, OVERTIME):
		out += _rows(doctype, filters)
	out.sort(key=lambda r: (str(r["date"] or ""), r["employee"] or "", r["name"]))
	return out


def _rows(doctype: str, filters: dict) -> list[dict]:
	is_overtime = doctype == OVERTIME
	date_field = "overtime_date" if is_overtime else "attendance_date"
	conds = [
		"r.docstatus = 1",
		"((r.source = 'Timesheet' AND ts.docstatus = 1) OR "
		"(IFNULL(r.source, 'Attendance') != 'Timesheet' AND fa.docstatus = 1))",
	]
	values: dict = {}

	projects = filters.get("projects")
	if filters.get("project"):
		projects = [filters["project"]]
	if projects is not None:
		projects = list(projects)
		if not projects:
			return []
		conds.append("r.project IN %(projects)s")
		values["projects"] = projects
	if filters.get("worker"):
		conds.append("r.employee = %(worker)s")
		values["worker"] = filters["worker"]
	if filters.get("from"):
		conds.append(f"r.{date_field} >= %(from_date)s")
		values["from_date"] = getdate(filters["from"])
	if filters.get("to"):
		conds.append(f"r.{date_field} <= %(to_date)s")
		values["to_date"] = getdate(filters["to"])
	if filters.get("source"):
		conds.append("IFNULL(r.source, 'Attendance') = %(source)s")
		values["source"] = filters["source"]

	if is_overtime:
		select = "r.overtime_hours AS ot_hours, r.overtime_wage_calculated AS ot_cost, NULL AS status, 0 AS regular_hours, 0 AS regular_cost"
	else:
		select = "0 AS ot_hours, 0 AS ot_cost, r.status AS status, r.regular_hours AS regular_hours, r.daily_wage_calculated AS regular_cost"

	rows = frappe.db.sql(
		f"""SELECT r.name, r.employee, r.employee_name, r.project, r.{date_field} AS date, r.task,
			r.field_attendance, r.timesheet, r.comments AS description,
			IFNULL(r.source, 'Attendance') AS source, r.full_day_hours,
			r.cost_code_type, r.cost_code_group, r.cost_code_item, r.cost_code_label,
			fa.cost_code_type AS fa_type, fa.cost_code_group AS fa_group,
			fa.cost_code_item AS fa_item, fa.cost_code_label AS fa_label,
			{select}
		FROM `tab{doctype}` r
		LEFT JOIN `tabField Attendance` fa ON fa.name = r.field_attendance
		LEFT JOIN `tabTimesheet` ts ON ts.name = r.timesheet
		WHERE {" AND ".join(conds)}""",  # server-built from the fixed fragments above; values are bound
		values,
		as_dict=True,
	)
	out = []
	for r in rows:
		full_day = flt(r.full_day_hours)
		regular = flt(r.regular_hours)
		out.append(
			{
				"doctype": doctype,
				"name": r.name,
				"source": r.source,
				"employee": r.employee,
				"employee_name": r.employee_name or r.employee,
				"project": r.project,
				"date": r.date,
				"task": r.task,
				"status": r.status,
				"field_attendance": r.field_attendance,
				"timesheet": r.timesheet,
				"description": r.description,
				"cost_code": _cost_code(r),
				"regular_hours": regular,
				"full_day_hours": full_day,
				"man_days": regular / full_day if full_day else 0.0,
				"regular_cost": flt(r.regular_cost),
				"ot_hours": flt(r.ot_hours),
				"ot_cost": flt(r.ot_cost),
			}
		)
	return out


def _cost_code(r) -> dict | None:
	"""The row's own cost code, else its parent sheet's (the header code)."""
	for t, g, i, label in (
		(r.cost_code_type, r.cost_code_group, r.cost_code_item, r.cost_code_label),
		(r.fa_type, r.fa_group, r.fa_item, r.fa_label),
	):
		if g or i:
			return {
				"type": (t or "").lower(),
				"group_code": g or "",
				"item_code": i or None,
				"label": label or "",
			}
	return None


def cost_of(row: dict) -> float:
	return flt(row["regular_cost"]) + flt(row["ot_cost"])


def totals(rows: list[dict]) -> dict:
	"""man_days, hours (regular + overtime), cost, for a set of rows from labour_cost_rows."""
	return {
		"man_days": round(sum(r["man_days"] for r in rows), 2),
		"regular_hours": sum(r["regular_hours"] for r in rows),
		"ot_hours": sum(r["ot_hours"] for r in rows),
		"cost": sum(cost_of(r) for r in rows),
	}


def labour_by_task(project: str, rows: list[dict]) -> dict:
	"""Labour cost per task: the rows whose task, or whose cost code's BOQ line's task, is that task.
	What no task claims is kept under the key None ("on no task") so it still counts in the total."""
	boqs = frappe.get_all("BOQ", filters={"project": project}, pluck="name")
	line_task = {
		i.code: i.task
		for i in frappe.get_all(
			"BOQ Item", filters={"boq": ["in", boqs or [""]], "task": ["is", "set"]}, fields=["code", "task"]
		)
	}
	out: dict = {}
	for r in rows:
		code = r["cost_code"]
		task = r["task"] or (line_task.get(code["item_code"]) if code and code["item_code"] else None)
		out[task] = out.get(task, 0.0) + cost_of(r)
	return out
