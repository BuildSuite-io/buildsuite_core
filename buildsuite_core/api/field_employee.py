# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted save for a Field Employee — an Employee with `is_labour` set.

Naming the fields here keeps the client out of Employee's ~100 other columns.
"""

import frappe
from frappe import _
from frappe.utils import flt

from buildsuite_core.utils.project import default_company

EMPLOYEE = "Employee"


def _parse_rows(payload) -> list:
	"""A JSON object parses to a truthy _dict and would iterate its keys."""
	rows = frappe.parse_json(payload) or []
	if not isinstance(rows, list):
		frappe.throw(_("Expected a list of rows."))
	return rows


def _apply_allocations(doc, rows: list) -> None:
	"""Replace the allocated-project rows, skipping blanks and duplicates."""
	doc.set("custom_project_assigned", [])
	seen = set()
	for row in rows:
		project = (row or {}).get("project")
		if not project or project in seen:
			continue
		seen.add(project)
		doc.append("custom_project_assigned", {"project": project})


@frappe.whitelist(methods=["POST"])
def save_field_employee(
	name: str | None = None,
	first_name: str | None = None,
	last_name: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
	date_of_joining: str | None = None,
	status: str | None = None,
	company: str | None = None,
	custom_trade: str | None = None,
	custom_contractor: str | None = None,
	cell_number: str | None = None,
	custom_wage: float | None = None,
	custom_wage_for_overtime: float | None = None,
	allocated_projects: str | None = None,
) -> dict:
	"""Create or update a field employee. `employee_name` is server-computed."""
	rows = _parse_rows(allocated_projects)

	first_name = (first_name or "").strip()
	if not first_name:
		frappe.throw(_("First name is required."))

	if name:
		if not frappe.db.exists(EMPLOYEE, name):
			frappe.throw(_("Field employee {0} no longer exists.").format(name))
		doc = frappe.get_doc(EMPLOYEE, name)
		doc.check_permission("write")
		# Without this, any Employee could be converted into a field worker.
		if not doc.is_labour:
			frappe.throw(_("{0} is not a field employee.").format(name))
	else:
		doc = frappe.new_doc(EMPLOYEE)
		doc.naming_series = "HR-EMP-"
		status = status or "Active"

	doc.is_labour = 1
	doc.first_name = first_name
	doc.last_name = (last_name or "").strip()
	doc.gender = gender
	doc.date_of_birth = date_of_birth
	doc.date_of_joining = date_of_joining
	doc.company = company or default_company()
	doc.custom_trade = custom_trade
	doc.custom_contractor = custom_contractor  # null clears it: blank = engaged directly
	doc.cell_number = (cell_number or "").strip()

	# Guarded: an omitted status must not revive a departed worker, and flt(None)
	# is 0.0 — which would zero the wage every attendance row is priced from.
	if status is not None:
		doc.status = status
	if custom_wage is not None:
		doc.custom_wage = flt(custom_wage)
	if custom_wage_for_overtime is not None:
		doc.custom_wage_for_overtime = flt(custom_wage_for_overtime)

	if allocated_projects is not None:
		_apply_allocations(doc, rows)

	doc.save()
	return {"name": doc.name}
