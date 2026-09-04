# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from collections import Counter

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

# --- tunables: move to a Settings doctype when the client asks ---
DAYS_PER_MONTH = 30
HOURS_PER_DAY = 8
MAX_OT_HOURS_PER_DAY = 16

# Rows above this count are processed in a background job on submit/cancel.
ENQUEUE_THRESHOLD = 25

# Field on the register doctypes that links back to Field Attendance.
REGISTER_SOURCE_FIELD = "field_attendance"

# Fieldname holding hours on Overtime Attendance Register.
OT_HOURS_FIELD = "overtime_hours"

# Field Attendance status -> Labour Attendance Register status
STATUS_MAP = {
	"Present": "Full Day",
	"Half Day": "Half Day",
	"Absent": "Absent",
}

# Statuses that may carry overtime hours
OT_ALLOWED_STATUSES = ("Present", "Half Day", "Overtime Only")


class FieldAttendance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.field_attendance_employee.field_attendance_employee import FieldAttendanceEmployee
		from frappe.types import DF

		amended_from: DF.Link | None
		comments: DF.SmallText | None
		date: DF.Date
		employee_list: DF.Table[FieldAttendanceEmployee]
		naming_series: DF.Literal["HR-FA-.YYYY.-"]
		overtime_hours: DF.Float
		project: DF.Link
		project_name: DF.Data | None
		status: DF.Literal["", "Present", "Half Day", "Absent", "Overtime Only"]
	# end: auto-generated types

	def validate(self):
		self.validate_rows_present()

		emp_map = self.get_employee_map()
		leave_map = self.get_leave_map()
		la_map, ot_map = self.get_register_maps()
		structure_cache = {}

		for row in self.employee_list:
			emp = emp_map.get(row.employee)
			if not emp:
				frappe.throw(_("Row {0}: Employee {1} not found.").format(row.idx, row.employee))

			emp_name = emp.employee_name or row.employee

			self.validate_employee_active(emp, emp_name)
			self.validate_joining_date(emp, emp_name)
			self.validate_not_on_leave(row.employee, emp_name, leave_map)
			self.validate_overtime_hours(row, emp_name)
			self.validate_against_registers(
				row,
				emp_name,
				la_map.get(row.employee, []),
				ot_map.get(row.employee, []),
			)
			row.labour_rate, row.overtime_rate = get_employee_rates(
				emp, self.date, structure_cache
			)


	# ------------------------------------------------------------------
	# submit / cancel
	# ------------------------------------------------------------------

	def on_submit(self):
		if len(self.employee_list) > ENQUEUE_THRESHOLD:
			frappe.enqueue(
				create_registers,
				queue="long",
				timeout=1500,
				enqueue_after_commit=True,
				doc_name=self.name,
			)
			frappe.msgprint(
				_("Attendance registers are being created in the background."),
				indicator="blue",
				alert=True,
			)
		else:
			create_registers(self.name)

	def on_cancel(self):
		if len(self.employee_list) > ENQUEUE_THRESHOLD:
			frappe.enqueue(
				cancel_registers,
				queue="long",
				timeout=1500,
				enqueue_after_commit=True,
				doc_name=self.name,
			)
			frappe.msgprint(
				_("Attendance registers are being cancelled in the background."),
				indicator="blue",
				alert=True,
			)
		else:
			cancel_registers(self.name)

	# ------------------------------------------------------------------
	# row / list level
	# ------------------------------------------------------------------

	def validate_rows_present(self):
		if not self.employee_list:
			frappe.throw(_("Employee list cannot be empty."))

		emp_ids = []
		for row in self.employee_list:
			if not row.employee:
				frappe.throw(_("Row {0}: Employee is required.").format(row.idx))

			if not row.status:
				frappe.throw(_("Row {0}: Attendance status is required.").format(row.idx))

			if row.status == "Overtime Only" and flt(row.overtime_hours) <= 0:
				frappe.throw(
					_("Row {0}: Overtime hours are required when status is Overtime Only.").format(
						row.idx
					)
				)

			emp_ids.append(row.employee)

		dupes = [e for e, count in Counter(emp_ids).items() if count > 1]
		if dupes:
			frappe.throw(
				_("The same employee appears more than once: {0}").format(", ".join(dupes))
			)

	# ------------------------------------------------------------------
	# batch lookups - one query each instead of one per row
	# ------------------------------------------------------------------

	def employee_ids(self):
		return list({row.employee for row in self.employee_list if row.employee})

	def get_employee_map(self):
		emp_ids = self.employee_ids()
		if not emp_ids:
			return {}

		fields = [
			"name",
			"employee_name",
			"status",
			"date_of_joining",
			"custom_wage",
			"custom_wage_for_overtime",
		]
		if "buildsuite_hr" in frappe.get_installed_apps():
			fields.append("custom_labour_wage_type")

		return {
			d.name: d
			for d in frappe.get_all("Employee", filters={"name": ["in", emp_ids]}, fields=fields)
		}

	def get_leave_map(self):
		"""employee -> True if on approved leave on self.date."""
		if "hrms" not in frappe.get_installed_apps():
			return {}

		emp_ids = self.employee_ids()
		if not emp_ids:
			return {}

		on_leave = frappe.get_all(
			"Leave Application",
			filters={
				"employee": ["in", emp_ids],
				"status": "Approved",
				"docstatus": 1,
				"from_date": ["<=", self.date],
				"to_date": [">=", self.date],
			},
			pluck="employee",
		)
		return {emp: True for emp in on_leave}

	def get_register_maps(self):
		"""Existing submitted register rows for this date, grouped by employee."""
		emp_ids = self.employee_ids()
		if not emp_ids:
			return {}, {}

		la_filters = {
			"employee": ["in", emp_ids],
			"attendance_date": self.date,
			"docstatus": 1,
		}
		ot_filters = {
			"employee": ["in", emp_ids],
			"overtime_date": self.date,
			"docstatus": 1,
		}

		la_map, ot_map = {}, {}

		for d in frappe.get_all(
			"Labour Attendance Register", filters=la_filters, fields=["name", "employee", "status"]
		):
			la_map.setdefault(d.employee, []).append(d)

		for d in frappe.get_all(
			"Overtime Attendance Register",
			filters=ot_filters,
			fields=["name", "employee", OT_HOURS_FIELD],
		):
			ot_map.setdefault(d.employee, []).append(d)

		return la_map, ot_map

	# ------------------------------------------------------------------
	# per-row checks
	# ------------------------------------------------------------------

	def validate_employee_active(self, emp, emp_name):
		if emp.status != "Active":
			frappe.throw(_("{0}: Employee is not Active.").format(emp_name))

	def validate_joining_date(self, emp, emp_name):
		if not emp.date_of_joining:
			frappe.throw(_("Joining Date not found for Employee {0}").format(emp_name))

		if getdate(self.date) < getdate(emp.date_of_joining):
			frappe.throw(
				_("{0}: Attendance date {1} is before the joining date {2}.").format(
					emp_name, self.date, emp.date_of_joining
				)
			)

	def validate_not_on_leave(self, employee, emp_name, leave_map):
		if leave_map.get(employee):
			frappe.throw(
				_(
					"Cannot mark attendance for {0} because an approved Leave Application exists for {1}."
				).format(emp_name, self.date)
			)

	def validate_overtime_hours(self, row, emp_name):
		hours = flt(row.overtime_hours)

		if hours < 0:
			frappe.throw(_("{0}: Overtime hours cannot be negative.").format(emp_name))

		if hours == 0:
			return

		if row.status not in OT_ALLOWED_STATUSES:
			frappe.throw(
				_("{0}: Cannot enter overtime hours when status is marked as {1}.").format(
					emp_name, row.status
				)
			)

	def validate_against_registers(self, row, emp_name, existing_la, existing_ot):
		has_full = any(d.status == "Full Day" for d in existing_la)
		has_absent = any(d.status == "Absent" for d in existing_la)
		half_count = sum(1 for d in existing_la if d.status == "Half Day")

		# --- overtime: capped by daily total rather than blocked outright ---
		existing_ot_hours = sum(flt(d.get(OT_HOURS_FIELD)) for d in existing_ot)
		total_ot = existing_ot_hours + flt(row.overtime_hours)

		if total_ot > MAX_OT_HOURS_PER_DAY:
			frappe.throw(
				_(
					"{0}: Total overtime for {1} would be {2} hours ({3} already recorded), "
					"over the {4} hour daily limit."
				).format(
					emp_name,
					self.date,
					total_ot,
					existing_ot_hours,
					MAX_OT_HOURS_PER_DAY,
				)
			)

		if row.status == "Overtime Only":
			if has_absent:
				frappe.throw(
					_("{0}: Cannot mark Overtime because Absent is already marked for {1}.").format(
						emp_name, self.date
					)
				)
			return

		if existing_ot and row.status not in OT_ALLOWED_STATUSES:
			frappe.throw(
				_("{0}: Cannot mark {1} because Overtime is already marked for {2}.").format(
					emp_name, row.status, self.date
				)
			)

		mapped = STATUS_MAP.get(row.status)

		if has_full:
			frappe.throw(_("{0}: Already marked Full Day on {1}.").format(emp_name, self.date))

		if mapped == "Full Day" and half_count:
			frappe.throw(
				_("{0}: Cannot mark Present because a Half Day is already marked for {1}.").format(
					emp_name, self.date
				)
			)

		if mapped == "Half Day" and half_count >= 2:
			frappe.throw(
				_("{0}: Only 2 Half Day attendances are allowed on {1}.").format(
					emp_name, self.date
				)
			)

		if mapped == "Absent" and (half_count or has_full):
			frappe.throw(
				_("{0}: Cannot mark Absent because attendance is already marked for {1}.").format(
					emp_name, self.date
				)
			)


# ----------------------------------------------------------------------
# register creation / cancellation
# ----------------------------------------------------------------------

def create_registers(doc_name):
	"""Create the Labour / Overtime register entries for a submitted Field Attendance.

	Safe to re-run: rows that already have a submitted register are skipped, so a
	retried background job will not double-post.
	"""
	doc = frappe.get_doc("Field Attendance", doc_name)

	existing_la = set(
		frappe.get_all(
			"Labour Attendance Register",
			filters={REGISTER_SOURCE_FIELD: doc_name, "docstatus": ["<", 2]},
			pluck="employee",
		)
	)
	existing_ot = set(
		frappe.get_all(
			"Overtime Attendance Register",
			filters={REGISTER_SOURCE_FIELD: doc_name, "docstatus": ["<", 2]},
			pluck="employee",
		)
	)

	for row in doc.employee_list:
		mapped = STATUS_MAP.get(row.status)

		if mapped and row.employee not in existing_la:
			create_labour_attendance(
				employee=row.employee,
				date=doc.date,
				project=doc.project,
				status=mapped,
				reference=doc.name,
				comments=row.comments,
				wage_rate=row.labour_rate,
			)

		if flt(row.overtime_hours) > 0 and row.employee not in existing_ot:
			create_overtime_attendance(
				employee=row.employee,
				date=doc.date,
				project=doc.project,
				overtime_hours=row.overtime_hours,
				reference=doc.name,
				comments=row.comments,
				overtime_rate=row.overtime_rate,
			)


def cancel_registers(doc_name):
	"""Cancel every submitted register entry created by this Field Attendance."""
	for doctype in ("Labour Attendance Register", "Overtime Attendance Register"):
		names = frappe.get_all(
			doctype,
			filters={REGISTER_SOURCE_FIELD: doc_name, "docstatus": 1},
			pluck="name",
		)

		for name in names:
			reg = frappe.get_doc(doctype, name)
			reg.flags.ignore_permissions = True
			reg.cancel()


def create_labour_attendance(employee, date, project, status, reference, comments, wage_rate):
	doc = frappe.get_doc(
		{
			"doctype": "Labour Attendance Register",
			"employee": employee,
			"attendance_date": date,
			"project": project,
			"status": status,
			"wage_rate": wage_rate,
			REGISTER_SOURCE_FIELD: reference,
			"comments": comments,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


def create_overtime_attendance(
	employee, date, project, overtime_hours, reference, comments, overtime_rate
):
	doc = frappe.get_doc(
		{
			"doctype": "Overtime Attendance Register",
			"employee": employee,
			"overtime_date": date,
			"project": project,
			"overtime_rate": overtime_rate,
			OT_HOURS_FIELD: overtime_hours,
			REGISTER_SOURCE_FIELD: reference,
			"comments": comments,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


# ----------------------------------------------------------------------
# rates
# ----------------------------------------------------------------------

def get_employee_rates(emp, date, structure_cache=None):
	"""`emp` is a dict from get_employee_map(), not an employee id."""
	if structure_cache is None:
		structure_cache = {}

	wage_rates = (flt(emp.custom_wage), flt(emp.custom_wage_for_overtime))

	if "buildsuite_hr" not in frappe.get_installed_apps():
		return wage_rates

	if emp.get("custom_labour_wage_type") != "Salaried":
		return wage_rates

	salary_structure = frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": emp.name, "from_date": ("<=", date), "docstatus": 1},
		"salary_structure",
		order_by="from_date desc",
	)

	if not salary_structure:
		frappe.throw(
			_("Salary Structure Assignment not found for {0} as on {1}.").format(
				emp.employee_name or emp.name, date
			)
		)

	if salary_structure not in structure_cache:
		doc = frappe.get_doc("Salary Structure", salary_structure)
		net = sum(flt(e.amount) for e in doc.earnings) - sum(flt(d.amount) for d in doc.deductions)

		if net <= 0:
			frappe.throw(
				_(
					"Salary Structure {0} evaluates to a net of zero. "
					"Formula-based components need amounts before they can be used here."
				).format(salary_structure)
			)

		labour_rate = net / DAYS_PER_MONTH
		structure_cache[salary_structure] = (labour_rate, labour_rate / HOURS_PER_DAY)

	return structure_cache[salary_structure]


# ----------------------------------------------------------------------
# whitelisted helpers
# ----------------------------------------------------------------------

def _labour_filters():
	"""Employment filter differs depending on whether hrms is on the site."""
	if "hrms" in frappe.get_installed_apps():
		return {"employment_type": "Labour"}
	return {"is_labour": 1}


@frappe.whitelist()
def get_employees(date: str, project: str | None = None):
	frappe.has_permission("Field Attendance", throw=True)

	leave_emps = []
	if "hrms" in frappe.get_installed_apps():
		leave_emps = frappe.get_all(
			"Leave Application",
			filters={
				"status": "Approved",
				"docstatus": 1,
				"from_date": ["<=", date],
				"to_date": [">=", date],
			},
			pluck="employee",
		)

	filters = {"status": "Active"}
	filters.update(_labour_filters())

	if leave_emps:
		filters["name"] = ["not in", leave_emps]

	return frappe.get_all(
		"Employee",
		filters=filters,
		fields=["name", "employee_name"],
		order_by="employee_name asc",
	)


@frappe.whitelist()
def get_assigned_employees(project: str):
	frappe.has_permission("Field Attendance", throw=True)

	if "hrms" in frappe.get_installed_apps():
		labour_condition = "e.employment_type = 'Labour'"
	else:
		labour_condition = "e.is_labour = 1"

	return frappe.db.sql_list(
		f"""
		SELECT pa.parent
		FROM `tabProject Assigned` pa
		JOIN `tabEmployee` e ON e.name = pa.parent
		WHERE pa.parenttype = 'Employee'
		  AND pa.project = %s
		  AND e.status = 'Active'
		  AND {labour_condition}
		""",
		(project,),
	)


@frappe.whitelist()
def get_last_day_attendance(project: str, current_date: str):
	frappe.has_permission("Field Attendance", throw=True)

	last_doc = frappe.db.get_value(
		"Field Attendance",
		{
			"project": project,
			"date": ["<", current_date],
			"docstatus": ["<", 2],
		},
		"name",
		order_by="date desc, creation desc",
	)

	if not last_doc:
		return []

	return frappe.get_all(
		"Field Attendance Employee",
		filters={"parent": last_doc, "parenttype": "Field Attendance"},
		fields=["employee", "employee_name"],
		parent="Field Attendance",
		order_by="idx asc",
	)