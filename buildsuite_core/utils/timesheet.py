# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Timesheet costing.

A timesheet row is costed at the worker's hourly rate: the daily rate over the full day of the row's
project (utils.full_day), or the worker's own hourly overtime rate for an overtime row. The row keeps
the full day, rate and amount it was costed with; they are recalculated on every save while the
timesheet is a draft and frozen on submit, so a later wage or setting change cannot reprice it.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from buildsuite_core.utils.full_day import get_full_day_hours

COST_CODE_FIELDS = (
	"custom_cost_code_type",
	"custom_cost_code_group",
	"custom_cost_code_item",
	"custom_cost_code_label",
)


def hourly_rates(employee, date, full_day_hours: float, cache: dict | None = None):
	"""(regular, overtime) cost per hour for a worker on a day with this full day. Regular is the daily
	rate over the full day, rounded to 2 places like the amount; overtime is the worker's own hourly
	overtime rate. A salaried worker's rates come from their salary structure."""
	from buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance import (
		get_employee_rates,
	)

	emp = employee if hasattr(employee, "get") else frappe.get_doc("Employee", employee)
	daily, overtime = get_employee_rates(emp, date, cache if cache is not None else {}, full_day_hours)
	return round(flt(daily) / flt(full_day_hours), 2), flt(overtime)


def row_cost_code(row) -> dict | None:
	"""The picker-shaped cost code stored on a timesheet row, or None."""
	if not row.get("custom_cost_code_label"):
		return None
	return {
		"type": (row.get("custom_cost_code_type") or "").lower(),
		"group_code": row.get("custom_cost_code_group") or "",
		"item_code": row.get("custom_cost_code_item") or None,
		"label": row.get("custom_cost_code_label") or "",
	}


def cost_code_fields(cost_code) -> dict:
	"""Flatten a picker cost code into the four stored fields (or blanks)."""
	if not cost_code or not isinstance(cost_code, dict):
		return dict.fromkeys(COST_CODE_FIELDS, "")
	return {
		"custom_cost_code_type": "Item" if cost_code.get("type") == "item" else "Group",
		"custom_cost_code_group": cost_code.get("group_code") or "",
		"custom_cost_code_item": cost_code.get("item_code") or "",
		"custom_cost_code_label": cost_code.get("label") or "",
	}


def cost_timesheet(doc, method=None):
	"""Timesheet validate: check row cost codes, then cost every row while the timesheet is a draft."""
	if doc.docstatus != 0:
		return
	_check_cost_codes(doc)
	if not doc.employee:
		return

	day = None
	for row in doc.time_logs:
		if row.from_time:
			day = getdate(row.from_time)
			break
	employee = frappe.get_doc("Employee", doc.employee)
	cache: dict = {}
	total = 0.0
	for row in doc.time_logs:
		row.full_day_hours = get_full_day_hours(row.project, doc.company)
		regular, overtime = hourly_rates(employee, day or getdate(), row.full_day_hours, cache)
		row.costing_rate = overtime if row.is_overtime else regular
		row.costing_amount = round(flt(row.hours) * flt(row.costing_rate), 2)
		total += row.costing_amount
	doc.total_costing_amount = total


def _check_cost_codes(doc):
	"""A row's code must be a group or line of its project's approved estimate. A row moved to
	another project loses its code: a code belongs to one project's estimate."""
	before = doc.get_doc_before_save()
	before_project = {r.name: r.project for r in (before.time_logs if before else [])}
	codes_cache: dict = {}
	for row in doc.time_logs:
		if not (row.custom_cost_code_group or row.custom_cost_code_item):
			continue
		if row.name in before_project and before_project[row.name] != row.project:
			row.update(cost_code_fields(None))
			continue
		if not row.project:
			frappe.throw(_("Row {0}: pick the project before a cost code.").format(row.idx))
		if row.project not in codes_cache:
			from buildsuite_core.api.subcontract import get_project_cost_codes

			codes_cache[row.project] = get_project_cost_codes(row.project)
		match = _find_code(row, codes_cache[row.project])
		if not match:
			frappe.throw(
				_("Row {0}: cost code {1} is not on the estimate of {2}.").format(
					row.idx, row.custom_cost_code_item or row.custom_cost_code_group, row.project
				)
			)
		row.update(cost_code_fields({**match, "type": match["type"].lower()}))


def _find_code(row, codes):
	is_item = bool(row.custom_cost_code_item)
	for c in codes:
		if is_item and c["type"] == "Item" and c["item_code"] == row.custom_cost_code_item:
			return c
		if not is_item and c["type"] == "Group" and c["group_code"] == row.custom_cost_code_group:
			return c
	return None
