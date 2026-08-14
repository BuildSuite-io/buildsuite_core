# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted save, roster and lifecycle for Field Attendance.

Draft -> Submit -> Cancel -> Amend. Submitting builds the Labour and Overtime
registers; cancelling reverses them. When a site configures a Frappe Workflow for
Field Attendance, submit and cancel refuse here and its transitions take over.

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
	status: str | None = None,
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
		status = status or "Present"

	doc.project = project
	doc.date = date

	# Guarded: None means "not sent", so a partial update must not reset a saved
	# "Absent" header to Present or blank the hours and comments.
	if status is not None:
		doc.status = status
	if overtime_hours is not None:
		doc.overtime_hours = overtime_hours
	if comments is not None:
		doc.comments = comments

	doc.set("employee_list", [])
	for row in rows:
		row = row or {}
		if not row.get("employee"):
			continue
		doc.append("employee_list", {k: row.get(k) for k in _ROW_FIELDS})

	doc.save()
	return _serialize(doc)


@frappe.whitelist()
def get_roster(project: str) -> list[dict]:
	"""Workers allocated to this project, as [{employee, employee_name}]."""
	if not project:
		frappe.throw(_("Project is required."))

	# The helper returns bare ids — resolve names for the picker. get_list, not
	# get_all: the gate upstream only checks Field Attendance, so Employee's own
	# permissions and user permissions still have to apply here.
	ids = get_assigned_employees(project)
	if not ids:
		return []
	rows = frappe.get_list(
		"Employee",
		filters={"name": ["in", ids]},
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)
	return [{"employee": r.name, "employee_name": r.employee_name or r.name} for r in rows]


def _guard_workflow():
	"""An active workflow owns submit and cancel; stop these endpoints bypassing it."""
	from buildsuite_core.api.workflow import workflow_active

	if workflow_active(FIELD_ATTENDANCE):
		frappe.throw(_("Field Attendance is governed by a workflow — use a workflow action."))


@frappe.whitelist(methods=["POST"])
def submit_field_attendance(name: str) -> dict:
	"""Post the sheet. on_submit builds the Labour and Overtime registers — over
	25 rows that runs in the background, so they may appear a moment later."""
	_guard_workflow()
	doc = frappe.get_doc(FIELD_ATTENDANCE, name)
	doc.submit()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def cancel_field_attendance(name: str) -> dict:
	"""Reverse a posted sheet — its register entries are cancelled with it."""
	_guard_workflow()
	doc = frappe.get_doc(FIELD_ATTENDANCE, name)
	doc.cancel()
	return _serialize(doc)


@frappe.whitelist(methods=["POST"])
def amend_field_attendance(name: str) -> dict:
	"""A draft copy of a cancelled sheet; the original stays cancelled."""
	src = frappe.get_doc(FIELD_ATTENDANCE, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled sheet can be amended."))
	if frappe.db.exists(FIELD_ATTENDANCE, {"amended_from": name}):
		frappe.throw(_("This sheet is already amended."))

	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	amended.workflow_state = None
	amended.insert()
	return _serialize(amended)
