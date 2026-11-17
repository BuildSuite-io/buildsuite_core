# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import *
from frappe.utils import flt, getdate

from buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance import MAX_OT_HOURS_PER_DAY
from buildsuite_core.utils.full_day import get_full_day_hours

# A day has 24 hours: regular + overtime across every register row can't exceed it.
MAX_HOURS_IN_A_DAY = 24


class OvertimeAttendanceRegister(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		comments: DF.SmallText | None
		company: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		field_attendance: DF.Link | None
		full_day_hours: DF.Float
		naming_series: DF.Literal["HR-OTATT-.YYYY.-"]
		overtime_date: DF.Date
		overtime_hours: DF.Float
		overtime_rate: DF.Currency
		overtime_wage_calculated: DF.Currency
		project: DF.Link
		project_name: DF.Data | None
		source: DF.Literal["Attendance", "Timesheet"]
		timesheet: DF.Link | None
		timesheet_detail: DF.Data | None
	# end: auto-generated types

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		naming_series: DF.Literal["HR-OTATT-.YYYY.-"]
		overtime_date: DF.Date
		overtime_hours: DF.Float
		overtime_rate: DF.Currency
		overtime_wage_calculated: DF.Currency
		project: DF.Link
		project_name: DF.Data | None
		working_hours: DF.Float

	def before_save(self):
		# A timesheet row arrives priced: it keeps the rate it was costed with.
		if self.source != "Timesheet":
			self.overtime_rate = get_employee_rates(
				self.employee, self.overtime_date, project=self.project, company=self.company
			)

	def validate(self):
		if self.source == "Timesheet":
			# Its parent is a timesheet, not a muster: no regular-attendance rules, and the wage is the
			# timesheet row's costing amount, already set.
			if flt(self.overtime_hours) <= 0:
				frappe.throw(_("Overtime hours cannot be zero!"))
		else:
			self.validate_date_ot_and_rate()
		self.set_full_day_hours()

	def set_full_day_hours(self):
		"""The full day this row was made with. Rows from a Field Attendance sheet arrive with the
		sheet's frozen value; a hand-made draft takes the helper's. Never touched once submitted."""
		if self.docstatus != 0:
			return
		if not self.source:
			self.source = "Attendance"
		if not flt(self.full_day_hours):
			self.full_day_hours = get_full_day_hours(self.project, self.company)

	def before_submit(self):
		self.validate_hours_in_a_day()

	def validate_hours_in_a_day(self):
		"""A worker can't log more than 24 hours on one day. Counts, for the day: the sheet's own row
		as its full day (Present) or half of it (Half Day) - the sheet's full day, not a fixed 8 and
		4 - plus the regular hours and overtime of the worker's other submitted register rows."""
		regular = 0.0
		if self.field_attendance:
			sheet_status = frappe.db.get_value(
				"Field Attendance Employee",
				{"parent": self.field_attendance, "employee": self.employee},
				"status",
			)
			sheet_full_day = frappe.db.get_value("Field Attendance", self.field_attendance, "full_day_hours")
			sheet_full_day = flt(sheet_full_day) or get_full_day_hours(self.project, self.company)
			regular += sheet_full_day * {"Present": 1.0, "Half Day": 0.5}.get(sheet_status, 0.0)

		for row in frappe.get_all(
			"Labour Attendance Register",
			filters={"employee": self.employee, "attendance_date": self.overtime_date, "docstatus": 1},
			fields=["regular_hours", "field_attendance"],
		):
			# This sheet's own labour row is already counted above.
			if not (self.field_attendance and row.field_attendance == self.field_attendance):
				regular += flt(row.regular_hours)

		other_overtime = sum(
			flt(h)
			for h in frappe.get_all(
				"Overtime Attendance Register",
				filters={
					"employee": self.employee,
					"overtime_date": self.overtime_date,
					"docstatus": 1,
					"name": ["!=", self.name],
				},
				pluck="overtime_hours",
			)
		)
		total = regular + other_overtime + flt(self.overtime_hours)
		if total > MAX_HOURS_IN_A_DAY:
			frappe.throw(
				_(
					"{0}: {1} hours on {2} would be more than {3} hours in a day ({4} regular, {5} overtime)."
				).format(
					frappe.bold(self.employee_name or self.employee),
					total,
					frappe.bold(self.overtime_date),
					MAX_HOURS_IN_A_DAY,
					regular,
					other_overtime + flt(self.overtime_hours),
				)
			)

	def validate_date_ot_and_rate(self):
		docs = [
			x.get("status")
			for x in frappe.get_all(
				"Labour Attendance Register",
				{"attendance_date": self.overtime_date, "docstatus": 1, "employee": self.employee},
				["status"],
			)
		]
		# An "Overtime Only" row creates no Labour Attendance Register by design.
		row_status = self.field_attendance and frappe.db.get_value(
			"Field Attendance Employee",
			{"parent": self.field_attendance, "employee": self.employee},
			"status",
		)
		if not docs and row_status != "Overtime Only":
			frappe.throw(
				f"No regular attendance record found for labour {frappe.bold(self.employee_name)} for date {frappe.bold(self.overtime_date)}!"
			)
		if ("Half Day" in docs and docs.count("Half Day") != 2) or "Absent" in docs:
			frappe.throw(
				f"Cannot mark overtime as labour {frappe.bold(self.employee_name)} was not Present full day for date {frappe.bold(self.overtime_date)}"
			)
		OTR = frappe.qb.DocType("Overtime Attendance Register")

		existing_hours = (
			frappe.qb.from_(OTR)
			.select(Sum(OTR.overtime_hours))
			.where(
				(OTR.employee == self.employee)
				& (OTR.overtime_date == self.overtime_date)
				& (OTR.docstatus == 1)
				& (OTR.name != self.name)
			)
		).run()

		existing_hours = flt(existing_hours[0][0]) if existing_hours else 0.0
		total_overtime_hours = existing_hours + flt(self.overtime_hours)
		if total_overtime_hours and total_overtime_hours > MAX_OT_HOURS_PER_DAY:
			frappe.throw(
				_("{0}: Overtime for {1} would be {2} hours, over the {3} hour daily limit.").format(
					frappe.bold(self.employee_name),
					frappe.bold(self.overtime_date),
					total_overtime_hours,
					MAX_OT_HOURS_PER_DAY,
				)
			)
		if self.overtime_hours == 0:
			frappe.throw(_("Overtime hours cannot be zero!"))
		self.overtime_wage_calculated = flt(self.overtime_rate) * flt(self.overtime_hours)

	pass


@frappe.whitelist()
def update_wage(employee_id: str, wage: str):
	if not (employee_id and wage):
		return
	# Enforce write permission on the Employee before mutating its wage (was an
	# unguarded whitelisted write). db_set persists within the request transaction —
	# no manual commit needed.
	emp = frappe.get_doc("Employee", employee_id)
	emp.check_permission("write")
	emp.db_set("custom_wage_for_overtime", wage)
	return wage


# @frappe.whitelist()
# def project_list_query(doctype, txt, searchfield, start, page_len, filters):
# 	if filters:
# 		query = """
# 			SELECT
# 				pro.name as name,
# 				pro.project_name
# 			FROM
# 				`tabProject` as pro,
# 				`tabEmployee` as emp,
# 				`tabProject Assigned` as pa
# 			WHERE
# 				emp.name = %(employee)s AND
# 				emp.name = pa.parent AND
# 				pa.project = pro.name
# 			GROUP BY
# 				pro.name
# 			LIMIT %(start)s, %(page_len)s
# 		"""
# 		values = frappe.db.sql(query.format(**{
# 			}), {
# 			'employee': filters['employee'],
# 			'txt': "%{}%".format(txt),
# 			'start': start,
# 			'page_len': page_len
# 		})
# 		return values
def get_employee_rates(emp, date, project=None, company=None):
	"""`emp` is a dict from get_employee_map(), not an employee id. A salaried worker's hourly
	overtime rate is the daily rate over the project / company full day (utils.full_day)."""
	emp = frappe.get_doc("Employee", emp)
	wage_rates = flt(emp.custom_wage_for_overtime)

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

	if salary_structure:
		doc = frappe.get_doc("Salary Structure", salary_structure)
		net = sum(flt(e.amount) for e in doc.earnings) - sum(flt(d.amount) for d in doc.deductions)

		if net <= 0:
			frappe.throw(
				_(
					"Salary Structure {0} evaluates to a net of zero. "
					"Formula-based components need amounts before they can be used here."
				).format(salary_structure)
			)

		labour_rate = net / 30

	return labour_rate / get_full_day_hours(project, company)


# def validate_employee_date(employee, date):
#     emp = frappe.db.get_value("Employee", employee, ["employee_name", "date_of_joining"], as_dict=True)

#     if not emp:
#         frappe.throw(_("Employee {0} not found").format(employee))

#     if not emp.date_of_joining:
#         frappe.throw(_("Joining Date not found for Employee {0}").format(emp.employee_name))

#     if frappe.utils.getdate(date) < frappe.utils.getdate(emp.date_of_joining):
#         frappe.throw(
#             _("Date {0} is before the joining date {1} of Employee {2} ({3})")
#             .format(date, emp.date_of_joining, emp.employee_name, employee)
#         )
