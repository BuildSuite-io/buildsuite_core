# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted save + roster for Field Attendance. Draft only — submit and
cancel are deliberately absent (the controller can't submit "Overtime Only" or
"Half Day" + overtime, and the doctype has no `cancel` permission).

Row rates are not accepted; the doctype's validate() stamps them.
"""

import frappe
from frappe import _

from buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance import (
	get_assigned_employees,
)

FIELD_ATTENDANCE = "Field Attendance"

# The only columns read off each employee row — the client can't inject rates.
_ROW_FIELDS = ("employee", "status", "overtime_hours", "comments")


def _parse_rows(payload) -> list:
	"""A JSON object parses to a truthy _dict and would iterate its keys."""
	rows = frappe.parse_json(payload) or []
	if not isinstance(rows, list):
		frappe.throw(_("Expected a list of rows."))
	return rows


def _serialize(doc) -> dict:
	return {
		"name": doc.name,
		"project": doc.project,
		"project_name": doc.project_name,
		"date": str(doc.date) if doc.date else None,
		"status": doc.status,
		"overtime_hours": doc.overtime_hours,
		"comments": doc.comments,
		"docstatus": doc.docstatus,
		"amended_from": doc.amended_from,
		"employee_list": [
			{
				"name": row.name,
				"employee": row.employee,
				"employee_name": row.employee_name,
				"status": row.status,
				"overtime_hours": row.overtime_hours,
				"comments": row.comments,
				"labour_rate": row.labour_rate,
				"overtime_rate": row.overtime_rate,
			}
			for row in doc.employee_list
		],
	}


@frappe.whitelist()
def get_field_attendance(name: str) -> dict:
	doc = frappe.get_doc(FIELD_ATTENDANCE, name)
	doc.check_permission("read")
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def save_field_attendance(
	name: str | None = None,
	project: str | None = None,
	date: str | None = None,
	status: str = "Present",
	overtime_hours: float | None = None,
	comments: str | None = None,
	employee_list: str | None = None,
) -> dict:
	"""Create or update a draft attendance sheet (header + employee rows)."""
	rows = _parse_rows(employee_list)

	if not project:
		frappe.throw(_("Project is required."))
	if not date:
		frappe.throw(_("Date is required."))
	if not rows:
		frappe.throw(_("Add at least one employee."))

	if name:
		if not frappe.db.exists(FIELD_ATTENDANCE, name):
			# Otherwise a stale id creates a second sheet for the same day.
			frappe.throw(_("Attendance sheet {0} no longer exists.").format(name))
		doc = frappe.get_doc(FIELD_ATTENDANCE, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft attendance sheet can be edited."))
	else:
		doc = frappe.new_doc(FIELD_ATTENDANCE)
		doc.naming_series = "HR-FA-.YYYY.-"

	doc.project = project
	doc.date = date
	doc.status = status
	doc.overtime_hours = overtime_hours
	doc.comments = comments

	doc.set("employee_list", [])
	for row in rows:
		row = row or {}
		if not row.get("employee"):
			continue
		doc.append("employee_list", {k: row.get(k) for k in _ROW_FIELDS})

	doc.save()
	return _serialize(doc)


def _normalise(rows: list) -> list[dict]:
	"""The controller helpers return `name` or `employee`. Give one shape."""
	out = []
	for row in rows:
		employee = row.get("employee") or row.get("name")
		if employee:
			out.append({"employee": employee, "employee_name": row.get("employee_name") or employee})
	return out


@frappe.whitelist()
def get_roster(project: str) -> list[dict]:
	"""Workers allocated to this project, as [{employee, employee_name}]."""
	if not project:
		frappe.throw(_("Project is required."))

	# The helper returns bare ids — resolve names for the picker.
	ids = get_assigned_employees(project)
	if not ids:
		return []
	return _normalise(
		frappe.get_all(
			"Employee",
			filters={"name": ["in", ids]},
			fields=["name", "employee_name"],
			order_by="employee_name asc",
		)
	)
