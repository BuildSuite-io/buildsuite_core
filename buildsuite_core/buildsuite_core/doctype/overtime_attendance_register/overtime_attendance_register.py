# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import *
from frappe.model.document import Document
from frappe.utils import flt, getdate
from frappe.query_builder.functions import Sum


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
		naming_series: DF.Literal["HR-OTATT-.YYYY.-"]
		overtime_date: DF.Date
		overtime_hours: DF.Float
		overtime_rate: DF.Currency
		overtime_wage_calculated: DF.Currency
		project: DF.Link
		project_name: DF.Data | None
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
		self.overtime_rate = get_employee_rates(self.employee, self.overtime_date)

	def validate(self):
		self.validate_date_ot_and_rate()

	def validate_date_ot_and_rate(self):
		docs = [x.get("status") for x in frappe.get_all("Labour Attendance Register",{"attendance_date":self.overtime_date,"docstatus":1,"employee":self.employee},["status"])]
		if not docs:
			frappe.throw(
				f"No regular attendance record found for labour {frappe.bold(self.employee_name)} for date {frappe.bold(self.overtime_date)}!"
			)
		if ("Half Day" in docs and docs.count("Half Day") != 2) or  "Absent" in docs:
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
		if total_overtime_hours and total_overtime_hours >= 16:
			frappe.throw(
				f"Overtime already marked for labour {frappe.bold(self.employee_name)} for date {frappe.bold(self.overtime_date)}."
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
def get_employee_rates(emp, date):
	"""`emp` is a dict from get_employee_map(), not an employee id."""
	emp = frappe.get_doc("Employee",emp)
	wage_rates =  flt(emp.custom_wage_for_overtime)

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

	return labour_rate / 8

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
