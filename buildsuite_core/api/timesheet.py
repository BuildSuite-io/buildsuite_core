# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Timesheets for the SPA, on the native Timesheet doctype.

One worker, one day, rows of hours against a project and cost code. ERPNext's Timesheet wants times
and an activity type; the SPA only asks for hours, so rows are laid end to end from midnight and the
"Labour" activity type is used. Costing (utils.timesheet) runs in the doctype's own validate, so the
form, the import and Desk all price a row the same way."""

import io
import re

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, getdate

from buildsuite_core.utils.daily_hours import check_timesheet_day
from buildsuite_core.utils.full_day import get_full_day_hours
from buildsuite_core.utils.timesheet import cost_code_fields, row_cost_code

TIMESHEET = "Timesheet"
ACTIVITY_TYPE = "Labour"
MAX_HOURS_PER_DAY = 24


def _ensure_activity_type() -> str:
	if not frappe.db.exists("Activity Type", ACTIVITY_TYPE):
		frappe.get_doc({"doctype": "Activity Type", "activity_type": ACTIVITY_TYPE}).insert(
			ignore_permissions=True
		)
	return ACTIVITY_TYPE


def _project_name(project):
	return (frappe.db.get_value("Project", project, "project_name") if project else None) or project


def _serialize(doc) -> dict:
	rows = []
	for r in doc.time_logs:
		rows.append(
			{
				"name": r.name,
				"project": r.project,
				"project_name": _project_name(r.project),
				"cost_code": row_cost_code(r),
				"hours": flt(r.hours),
				"is_overtime": int(bool(r.is_overtime)),
				"description": r.description or "",
				"full_day_hours": flt(r.full_day_hours),
				"costing_rate": flt(r.costing_rate),
				"costing_amount": flt(r.costing_amount),
			}
		)
	return {
		"name": doc.name,
		"employee": doc.employee,
		"employee_name": doc.employee_name,
		"date": str(doc.start_date) if doc.start_date else None,
		"note": doc.note or "",
		"docstatus": doc.docstatus,
		"status": doc.status,
		"company": doc.company,
		"total_hours": flt(doc.total_hours),
		"total_costing_amount": flt(doc.total_costing_amount),
		"rows": rows,
	}


@frappe.whitelist()
def get_timesheet(name: str) -> dict:
	doc = frappe.get_doc(TIMESHEET, name)
	doc.check_permission("read")
	return _serialize(doc)


@frappe.whitelist()
def costing_info(employee: str, project: str | None = None, date: str | None = None) -> dict:
	"""What the form shows under the header: the worker's daily rate, the full day on the project and
	the hourly rate that makes ("an hour (daily rate ÷ h, the full day on Block A)"), plus overtime."""
	from buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance import (
		get_employee_rates,
	)

	emp = frappe.get_doc("Employee", employee)
	emp.check_permission("read")
	full_day = get_full_day_hours(project, emp.company)
	daily, overtime = get_employee_rates(emp, getdate(date), {}, full_day)
	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"trade": emp.get("custom_trade") or "",
		"daily_rate": flt(daily),
		"overtime_rate": flt(overtime),
		"full_day_hours": full_day,
		"hourly_rate": round(flt(daily) / flt(full_day), 2),
		"project": project,
		"project_name": _project_name(project),
	}


def _existing_for_day(employee, date, exclude=None):
	filters = {"employee": employee, "start_date": date, "docstatus": ["<", 2]}
	if exclude:
		filters["name"] = ["!=", exclude]
	return frappe.db.get_value(TIMESHEET, filters, "name")


def _build_rows(date, rows):
	"""Timesheet Detail rows from the SPA's rows, laid end to end from midnight."""
	activity = _ensure_activity_type()
	start = getdate(date)
	cursor = f"{start} 00:00:00"
	out = []
	for r in rows:
		hours = flt(r.get("hours"))
		out.append(
			{
				"activity_type": activity,
				"from_time": cursor,
				"hours": hours,
				"project": r.get("project"),
				"is_overtime": 1 if r.get("is_overtime") else 0,
				"description": r.get("description") or "",
				**cost_code_fields(r.get("cost_code")),
			}
		)
		cursor = add_to_date(cursor, hours=hours, as_string=True)
	return out


@frappe.whitelist()
def save_timesheet(
	employee: str,
	date: str,
	time_logs: str,
	name: str | None = None,
	note: str | None = None,
	submit: int = 0,
) -> dict:
	"""Create or update a draft timesheet (and submit it when asked)."""
	rows = [r for r in (frappe.parse_json(time_logs) or []) if r.get("project") or flt(r.get("hours"))]
	if not employee:
		frappe.throw(_("Pick an employee."))
	if not date:
		frappe.throw(_("Pick a date."))
	if not rows:
		frappe.throw(_("Add at least one row of hours."))
	for i, r in enumerate(rows, 1):
		if not r.get("project"):
			frappe.throw(_("Row {0}: pick a project.").format(i))
		if not (0 < flt(r.get("hours")) <= MAX_HOURS_PER_DAY):
			frappe.throw(_("Row {0}: hours must be above 0 and up to 24.").format(i))
	total = sum(flt(r.get("hours")) for r in rows)
	if total > MAX_HOURS_PER_DAY:
		frappe.throw(_("{0} hours in one day is more than 24.").format(total))
	if clash := _existing_for_day(employee, getdate(date), exclude=name):
		frappe.throw(
			_("{0} already has a timesheet for {1}: {2}.").format(
				frappe.db.get_value("Employee", employee, "employee_name") or employee, date, clash
			)
		)

	if name:
		doc = frappe.get_doc(TIMESHEET, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft timesheet can be changed."))
		doc.set("time_logs", [])
	else:
		doc = frappe.new_doc(TIMESHEET)
	doc.employee = employee
	doc.company = frappe.db.get_value("Employee", employee, "company")
	doc.note = note or ""
	for row in _build_rows(date, rows):
		doc.append("time_logs", row)
	doc.save()
	if frappe.utils.cint(submit):
		doc.submit()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def submit_timesheet(name: str) -> dict:
	doc = frappe.get_doc(TIMESHEET, name)
	doc.check_permission("submit")
	doc.submit()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def cancel_timesheet(name: str) -> dict:
	doc = frappe.get_doc(TIMESHEET, name)
	doc.check_permission("cancel")
	doc.cancel()
	return _serialize(doc)


# ---------------------------------------------------------------------------
# Excel template + import
# ---------------------------------------------------------------------------

# key -> (label, width, accepted headings). The first heading row with Hours and one more of these
# is the header; the Task column of the old template is recognised only to be flagged.
COLUMNS = (
	("date", "Date", 12, ("date", "work date", "day")),
	("emp_code", "Employee code", 16, ("employee code", "emp code", "employee id", "emp id", "code", "id")),
	("emp_name", "Employee name", 22, ("employee name", "employee", "name", "worker", "worker name")),
	("project", "Project code", 14, ("project code", "project", "job", "site", "project id")),
	("cost_code", "Cost code", 14, ("cost code", "costcode", "boq code", "boq line", "line code")),
	("hours", "Hours", 8, ("hours", "hrs", "hour", "hours worked")),
	("overtime", "Overtime (Y/N)", 14, ("overtime (y/n)", "overtime", "ot", "ot (y/n)", "is overtime")),
	("description", "Description", 36, ("description", "remarks", "notes", "work done", "details")),
)
LEGACY_TASK = ("task", "task id", "task name")


def _norm(v) -> str:
	return re.sub(r"\s+", " ", str(v if v is not None else "").lower()).strip()


def _labour_employees():
	"""Active field workers - the Employee rows flagged `is_labour`, the set every SPA worker picker
	(and the Field Employees list) offers."""
	return frappe.get_all(
		"Employee",
		filters={"is_labour": 1, "status": "Active"},
		fields=["name", "employee_name", "custom_trade", "custom_wage", "custom_wage_for_overtime"],
		order_by="employee_name asc",
	)


def _allocated_projects(employee):
	return frappe.get_all(
		"Project Assigned", filters={"parent": employee, "parenttype": "Employee"}, pluck="project"
	)


def _project_rows():
	return frappe.get_all(
		"Project", fields=["name", "project_name", "custom_project_id"], order_by="name asc"
	)


def _project_code(p):
	return p.get("custom_project_id") or p.name


def _codes_for(project):
	from buildsuite_core.api.subcontract import get_project_cost_codes

	return get_project_cost_codes(project) or []


def find_cost_code(value, options):
	"""A cost code as typed against one project's list. "B.04", "b.04" and "B.04 · Wardrobes" all find
	line B.04; "B" finds the group. Blank is None (not coded); not on the list is False."""
	k = _norm(str(value if value is not None else "").split("·")[0])
	if not k:
		return None
	for o in options:
		if _norm(o.get("item_code") or o.get("group_code")) == k:
			return {
				"type": o["type"].lower(),
				"group_code": o["group_code"],
				"item_code": o["item_code"] or None,
				"label": o["label"],
			}
	return False


@frappe.whitelist()
def timesheet_template(project: str | None = None, cost_code: str | None = None, date: str | None = None):
	"""Download the workbook to fill in. A chosen date and cost code are filled in on every row; a chosen
	project lists only the workers allocated to it (everyone when none is) and the Cost codes sheet
	lists that project's estimate - every project's when none is chosen."""
	from openpyxl import Workbook
	from openpyxl.styles import Font
	from openpyxl.utils import get_column_letter

	picked = frappe.parse_json(cost_code) if cost_code else None
	workers = _labour_employees()
	listed = workers
	if project:
		allocated = [w for w in workers if project in _allocated_projects(w.name)]
		listed = allocated or workers
	projects = _project_rows()
	chosen = next((p for p in projects if p.name == project), None)
	code = (picked.get("item_code") or picked.get("group_code") or "") if (picked and chosen) else ""

	wb = Workbook()
	sheets = [("Timesheet", [c[2] for c in COLUMNS], [[c[1] for c in COLUMNS]])]
	sheets[0][2].extend(
		[date or "", w.name, w.employee_name, _project_code(chosen) if chosen else "", code, "", "N", ""]
		for w in listed
	)
	sheets.append(
		(
			"Employees",
			[16, 24, 16, 12, 18],
			[["Employee code", "Name", "Trade", "Daily rate", "Overtime rate / hr"]]
			+ [
				[
					w.name,
					w.employee_name,
					w.custom_trade or "",
					flt(w.custom_wage),
					flt(w.custom_wage_for_overtime),
				]
				for w in workers
			],
		)
	)
	sheets.append(
		(
			"Projects",
			[14, 44],
			[["Project code", "Project"]] + [[_project_code(p), p.project_name or p.name] for p in projects],
		)
	)
	code_rows = []
	for p in [chosen] if chosen else projects:
		for o in _codes_for(p.name):
			desc = o["label"].split(" · ", 1)[1] if " · " in o["label"] else ""
			code_rows.append(
				[
					_project_code(p),
					o["item_code"] or o["group_code"],
					"Line" if o["type"] == "Item" else "Group",
					desc,
				]
			)
	sheets.append(
		("Cost codes", [14, 12, 8, 60], [["Project code", "Cost code", "Level", "Description"], *code_rows])
	)
	sheets.append(
		(
			"How to fill",
			[100],
			[
				["How to fill this timesheet"],
				[
					"One row per employee per project and cost code per day. Several rows for the same "
					"person and day become one timesheet."
				],
				["Date: YYYY-MM-DD, or day first such as 19/10/2026."],
				[
					"Employee code and Project code: from the Employees and Projects sheets. The name "
					"works if the code is left blank."
				],
				[
					"Cost code: a group (such as B) or a line (such as B.04) from the Cost codes sheet, "
					"on that project's estimate. It is where the hours land on the estimate. A row left "
					"without one still counts on the project, but on no estimate line."
				],
				[
					"Hours: up to 24 a day. Cost per hour is the worker's daily rate divided by the "
					"project's full day."
				],
				["Overtime: Y for overtime hours, costed at the overtime rate. Leave N otherwise."],
				["Rows with no hours are ignored, so you can leave the people who did not work blank."],
			],
		)
	)
	wb.remove(wb.active)
	for title, widths, rows in sheets:
		ws = wb.create_sheet(title)
		for r in rows:
			ws.append(r)
		for i, w in enumerate(widths, 1):
			ws.column_dimensions[get_column_letter(i)].width = w
		for cell in ws[1]:
			cell.font = Font(bold=True)
	buf = io.BytesIO()
	wb.save(buf)
	frappe.response["filename"] = "timesheet-template.xlsx"
	frappe.response["filecontent"] = buf.getvalue()
	frappe.response["type"] = "download"


def _read_rows(filename: str, data: bytes) -> list[list]:
	if filename.lower().endswith(".csv"):
		import csv

		return [list(r) for r in csv.reader(io.StringIO(data.decode("utf-8-sig")))]
	from openpyxl import load_workbook

	wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
	ws = wb["Timesheet"] if "Timesheet" in wb.sheetnames else wb.worksheets[0]
	return [list(r) for r in ws.iter_rows(values_only=True)]


def _find_header(rows):
	for r in range(min(len(rows), 15)):
		mapping, legacy = {}, False
		for c, cell in enumerate(rows[r] or []):
			h = _norm(cell)
			if not h:
				continue
			legacy = legacy or h in LEGACY_TASK
			for key, label, _w, words in COLUMNS:
				if (h == label.lower() or h in words) and key not in mapping:
					mapping[key] = c
					break
		if "hours" in mapping and len(mapping) >= 2:
			return r, mapping, legacy and "cost_code" not in mapping
	return -1, {}, False


def _parse_date(v):
	import datetime

	if v in (None, ""):
		return ""
	if isinstance(v, datetime.datetime):
		return v.date().isoformat()
	if isinstance(v, datetime.date):
		return v.isoformat()
	s = str(v).strip()
	m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
	if m:
		y, mo, d = map(int, m.groups())
	else:
		m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$", s)
		if not m:
			return ""
		d, mo, y = map(int, m.groups())
		y += 2000 if y < 100 else 0
	try:
		return datetime.date(y, mo, d).isoformat()
	except ValueError:
		return ""


def _num(v):
	try:
		return float(str(v).strip().replace(",", ""))
	except TypeError, ValueError:
		return None


def plan_import(rows: list[list]) -> dict:
	"""What an upload would create: one group per worker per day, the rows left out and why."""
	header_row, mapping, legacy_task = _find_header(rows)
	if header_row < 0:
		return {"groups": [], "skipped": [], "blank": 0, "legacy_task": False, "header_found": False}

	def cell(r, key):
		return "" if key not in mapping or mapping[key] >= len(r) else r[mapping[key]]

	workers = {w.name: w for w in _labour_employees()}
	projects = _project_rows()
	codes_cache: dict = {}
	groups: dict = {}
	skipped, blank = [], 0

	def find_worker(code, name):
		c, n = _norm(code), _norm(name)
		for w in workers.values():
			if c and _norm(w.name) == c:
				return w
		for w in workers.values():
			if n and _norm(w.employee_name) == n:
				return w
		return None

	def find_project(v):
		k = _norm(v)
		return next(
			(
				p
				for p in projects
				if k and k in (_norm(p.name), _norm(p.custom_project_id), _norm(p.project_name))
			),
			None,
		)

	for i in range(header_row + 1, len(rows)):
		r = rows[i] or []
		row_no = i + 1
		if all(v in (None, "") or not str(v).strip() for v in (cell(r, c[0]) for c in COLUMNS)):
			continue
		hours_raw = cell(r, "hours")
		if str(hours_raw if hours_raw is not None else "").strip() == "":
			blank += 1
			continue
		worker = find_worker(cell(r, "emp_code"), cell(r, "emp_name"))
		if not worker:
			who = str(cell(r, "emp_code") or cell(r, "emp_name") or "").strip() or "no employee"
			skipped.append({"row_no": row_no, "reason": _('"{0}" is not in the employee list.').format(who)})
			continue
		date = _parse_date(cell(r, "date"))
		if not date:
			skipped.append(
				{
					"row_no": row_no,
					"reason": _('The date "{0}" could not be read.').format(
						str(cell(r, "date") or "").strip()
					),
				}
			)
			continue
		proj_raw = cell(r, "project")
		project = find_project(proj_raw)
		if not project:
			skipped.append(
				{
					"row_no": row_no,
					"reason": _('Project "{0}" was not found.').format(str(proj_raw).strip())
					if str(proj_raw or "").strip()
					else _("No project."),
				}
			)
			continue
		if project.name not in codes_cache:
			codes_cache[project.name] = _codes_for(project.name)
		code_raw = cell(r, "cost_code")
		cost_code = find_cost_code(code_raw, codes_cache[project.name])
		if cost_code is False:
			skipped.append(
				{
					"row_no": row_no,
					"reason": _('Cost code "{0}" is not on the estimate of {1}.').format(
						str(code_raw).strip(), project.project_name or project.name
					),
				}
			)
			continue
		hours = _num(hours_raw)
		if hours is None or not (0 < hours <= MAX_HOURS_PER_DAY):
			skipped.append(
				{
					"row_no": row_no,
					"reason": _('Hours "{0}" must be a number above 0 and up to 24.').format(
						str(hours_raw).strip()
					),
				}
			)
			continue
		is_ot = bool(re.match(r"^(y|yes|true|1|ot|overtime)$", str(cell(r, "overtime") or "").strip(), re.I))
		key = f"{worker.name}|{date}"
		group = groups.setdefault(
			key,
			{
				"key": key,
				"employee": worker.name,
				"employee_name": worker.employee_name,
				"date": date,
				"rows": [],
			},
		)
		group["rows"].append(
			{
				"row_no": row_no,
				"project": project.name,
				"project_name": project.project_name or project.name,
				"cost_code": cost_code,
				"hours": hours,
				"is_overtime": int(is_ot),
				"description": str(cell(r, "description") or "").strip(),
			}
		)

	out = []
	for g in groups.values():
		g["hours"] = round(sum(x["hours"] for x in g["rows"]), 2)
		g["problem"] = None
		if _existing_for_day(g["employee"], getdate(g["date"])):
			g["problem"] = _("{0} already has a timesheet for {1}.").format(g["employee_name"], g["date"])
		elif g["hours"] > MAX_HOURS_PER_DAY:
			g["problem"] = _("{0} hours in one day is more than 24.").format(g["hours"])
		else:
			# The same check a save runs, so a day that would be refused isn't marked Ready.
			g["problem"] = check_timesheet_day(
				g["employee"],
				getdate(g["date"]),
				[
					{
						"hours": x["hours"],
						"is_overtime": x["is_overtime"],
						"full_day_hours": get_full_day_hours(x["project"]),
					}
					for x in g["rows"]
				],
			)
		out.append(g)
	out.sort(key=lambda g: (g["date"], g["employee_name"]))
	return {
		"groups": out,
		"skipped": skipped,
		"blank": blank,
		"legacy_task": legacy_task,
		"header_found": True,
	}


@frappe.whitelist(methods=["POST"])
def preview_import() -> dict:
	"""Read an uploaded .xlsx / .csv and say what it would create. Nothing is saved."""
	frappe.has_permission(TIMESHEET, "create", throw=True)
	f = frappe.request.files.get("file")
	if not f:
		frappe.throw(_("Choose a file to upload."))
	return plan_import(_read_rows(f.filename or "", f.read()))


@frappe.whitelist(methods=["POST"])
def create_timesheets(groups: str, submit: int = 0) -> dict:
	"""Create one timesheet per (worker, day) group from a previewed upload."""
	created, failed = [], []
	for i, g in enumerate(frappe.parse_json(groups) or []):
		save_point = f"timesheet_import_{i}"
		frappe.db.savepoint(save_point)
		try:
			doc = save_timesheet(
				employee=g["employee"],
				date=g["date"],
				time_logs=frappe.as_json(g["rows"]),
				submit=submit,
			)
			created.append(doc["name"])
		except Exception as e:
			frappe.db.rollback(save_point=save_point)
			failed.append({"key": g.get("key"), "reason": str(e)})
	return {"created": created, "failed": failed}
