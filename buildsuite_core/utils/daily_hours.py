# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Hours one worker can log on one day.

Two limits, counted across attendance and timesheets together (both end up as register rows):

* Regular time is at most one full day. Each regular hour is divided by the full day of its own
  project and the total can't exceed 1. Hours beyond that are entered as overtime.
* Regular plus overtime is at most 24 hours.

A timesheet is checked on every save against the worker's register rows that day (leaving out its
own); a Field Attendance sheet is checked when it is submitted, against the worker's timesheet rows.
Records that already exist are never re-checked.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from buildsuite_core.utils.full_day import REGULAR_HOURS_SHARE, get_full_day_hours

MAX_HOURS_IN_A_DAY = 24
# A day is "over" only past this, so 5 h of 10 + 4.5 h of 9 (1.0 exactly) never trips on float noise.
EPSILON = 1e-6

LABOUR = "Labour Attendance Register"
OVERTIME = "Overtime Attendance Register"


def _fmt(value) -> str:
	"""4.0 -> "4", 4.5 -> "4.5"."""
	return f"{round(flt(value), 2):g}"


def worker_name(employee) -> str:
	return frappe.db.get_value("Employee", employee, "employee_name") or employee


def booked_hours(employee, day, exclude_timesheet=None, exclude_sheet=None) -> dict:
	"""What the worker's submitted register rows already hold for `day`.

	regular_days: regular time as a share of a full day (each row over its own full day).
	regular_hours / overtime_hours: plain hours. by_source: which sources the regular time came from.
	"""
	out = {
		"regular_days": 0.0,
		"regular_hours": 0.0,
		"overtime_hours": 0.0,
		"attendance_days": 0.0,
		"timesheet_days": 0.0,
		"timesheet_regular_hours": 0.0,
	}
	for r in frappe.get_all(
		LABOUR,
		filters={"employee": employee, "attendance_date": day, "docstatus": 1},
		fields=["status", "regular_hours", "full_day_hours", "source", "timesheet", "field_attendance"],
	):
		if (exclude_timesheet and r.timesheet == exclude_timesheet) or (
			exclude_sheet and r.field_attendance == exclude_sheet
		):
			continue
		full_day = flt(r.full_day_hours) or get_full_day_hours()
		hours = (
			flt(r.regular_hours)
			if r.regular_hours not in (None, "")
			else full_day * REGULAR_HOURS_SHARE.get(r.status, 0.0)
		)
		days = hours / full_day
		out["regular_days"] += days
		out["regular_hours"] += hours
		if r.source == "Timesheet":
			out["timesheet_days"] += days
			out["timesheet_regular_hours"] += hours
		else:
			out["attendance_days"] += days
	for r in frappe.get_all(
		OVERTIME,
		filters={"employee": employee, "overtime_date": day, "docstatus": 1},
		fields=["overtime_hours", "timesheet"],
	):
		if exclude_timesheet and r.timesheet == exclude_timesheet:
			continue
		out["overtime_hours"] += flt(r.overtime_hours)
	return out


def check_timesheet_day(employee, day, rows, exclude_timesheet=None) -> str | None:
	"""The message for a timesheet's day if it breaks a limit, else None.

	rows: [{"hours", "is_overtime", "full_day_hours"}] - the timesheet's rows for that one day.
	"""
	own_regular_days = own_regular = own_overtime = 0.0
	overflow_full_day = None
	for r in rows:
		hours = flt(r.get("hours"))
		if r.get("is_overtime"):
			own_overtime += hours
			continue
		full_day = flt(r.get("full_day_hours")) or get_full_day_hours()
		own_regular += hours
		own_regular_days += hours / full_day
		overflow_full_day = full_day  # the last regular row's full day expresses the excess

	booked = booked_hours(employee, day, exclude_timesheet=exclude_timesheet)
	total_days = booked["regular_days"] + own_regular_days

	if own_regular_days and total_days > 1 + EPSILON:
		return _regular_message(employee, booked, own_regular, total_days, overflow_full_day)

	existing = booked["regular_hours"] + booked["overtime_hours"]
	here = own_regular + own_overtime
	if here and existing + here > MAX_HOURS_IN_A_DAY + EPSILON:
		return _("{0} hours here and {1} already on {2} that day is more than {3} hours.").format(
			_fmt(here), _fmt(existing), _source_label(booked), MAX_HOURS_IN_A_DAY
		)
	return None


def _source_label(booked) -> str:
	if booked["timesheet_days"] and not booked["attendance_days"]:
		return _("other timesheets")
	if booked["timesheet_days"]:
		return _("attendance and timesheets")
	return _("attendance")


def _regular_message(employee, booked, own_regular, total_days, full_day) -> str:
	if not booked["regular_days"]:
		return _(
			"{0} regular hours is more than the {1}-hour full day. Enter the {2} hours beyond it as overtime."
		).format(_fmt(own_regular), _fmt(full_day), _fmt((total_days - 1) * full_day))

	room = max(0.0, 1 - booked["regular_days"]) * full_day
	already = _("{0} already has {1} regular hours that day on {2}").format(
		worker_name(employee), _fmt(booked["regular_hours"]), _source_label(booked)
	)
	if room <= EPSILON:
		return _("{0}, so no more regular hours fit. Enter the rest as overtime.").format(already)
	return _(
		"{0}, so at most {1} regular hours fit here (the full day is {2} hours). Enter the rest as overtime."
	).format(already, _fmt(room), _fmt(full_day))


# --- doc_events ------------------------------------------------------------------------------


def validate_timesheet_hours(doc, method=None):
	"""Timesheet validate (every save, and again on submit): each day the timesheet touches must fit
	beside what the worker already has in the registers."""
	if doc.docstatus == 2 or not doc.employee:
		return
	days: dict = {}
	for row in doc.time_logs:
		if not row.from_time or not flt(row.hours):
			continue
		days.setdefault(getdate(row.from_time), []).append(
			{
				"hours": row.hours,
				"is_overtime": row.is_overtime,
				"full_day_hours": get_full_day_hours(row.project, doc.company),
			}
		)
	for day, rows in days.items():
		message = check_timesheet_day(doc.employee, day, rows, exclude_timesheet=doc.name)
		if message:
			frappe.throw(message, title=_("Too many hours in a day"))


def validate_attendance_hours(doc):
	"""Field Attendance before_submit: a worker marked Present (1 full day) or Half Day (0.5) can't
	also have timesheet regular time that takes the day past one full day."""
	share = {"Present": 1.0, "Half Day": 0.5}
	for row in doc.employee_list:
		if row.status not in share:
			continue
		booked = booked_hours(row.employee, doc.date, exclude_sheet=doc.name)
		if not booked["timesheet_days"]:
			continue
		if booked["timesheet_days"] + share[row.status] > 1 + EPSILON:
			full_day = flt(doc.full_day_hours) or get_full_day_hours(doc.project, doc.company)
			frappe.throw(
				_(
					"{0}: {1} regular hours on a timesheet that day and {2} here come to more than "
					"one full day ({3} hours). Mark the worker Half Day or Overtime Only here, or "
					"enter the timesheet hours beyond the full day as overtime."
				).format(
					row.employee_name or worker_name(row.employee),
					_fmt(booked["timesheet_regular_hours"]),
					_fmt(share[row.status] * full_day),
					_fmt(full_day),
				),
				title=_("Too many hours in a day"),
			)
