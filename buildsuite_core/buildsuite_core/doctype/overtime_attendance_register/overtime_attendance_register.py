# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import *
from frappe.model.document import Document


class OvertimeAttendanceRegister(Document):
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
		self.overtime_rate = frappe.db.get_value("Employee", self.employee, "custom_wage_for_overtime") or 0

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
		overtime_hours = frappe.db.get_value(
			"Overtime Attendance Register",
			{
				"employee": self.employee,
				"overtime_date": self.overtime_date,
				"docstatus": 1,
				"name": ["!=", self.name],
			},
			"SUM(overtime_hours) as overtime_hours"
		)
		total_overtime_hours = overtime_hours+self.overtime_hours if overtime_hours else self.overtime_hours 
		if total_overtime_hours and total_overtime_hours >= 16:
			frappe.throw(
				f"Overtime already marked for labour {frappe.bold(self.employee_name)} for date {frappe.bold(self.overtime_date)}."
			)
		if self.overtime_hours == 0:
			frappe.throw("Overtime hours cannot be zero!")
		self.overtime_wage_calculated = self.overtime_rate * self.overtime_hours
	pass
@frappe.whitelist()
def update_wage(employee_id, wage):
    if employee_id and wage:
        frappe.db.set_value("Employee",employee_id,'custom_wage_for_overtime',wage)
        frappe.db.commit()
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
    
# def get_employee_rates(employee, date):
#     # Returns the overtime rate as a scalar. The non-salaried branch used to
#     # return a (wage, ot_wage) tuple, which was assigned straight to the
#     # Currency field `overtime_rate` in before_save — that broke save_version's
#     # diff formatter (fmt_money does `amount % 1` and a tuple raises TypeError).
#     if frappe.db.get_value("Employee", employee, "custom_labour_wage_type") != "Salaried":
#         return frappe.db.get_value("Employee", employee, "custom_wage_for_overtime") or 0


#     validate_employee_date(employee, date)

#     salary_structure = frappe.db.get_value(
#         "Salary Structure Assignment",
#         {"employee": employee, "from_date": ("<=", date)},
#         "salary_structure",
#         order_by="from_date desc"
#     )

#     if not salary_structure:
#         frappe.throw(f"Salary Structure not found for employee {employee}")

#     doc = frappe.get_doc("Salary Structure", salary_structure)

#     net = sum(e.amount for e in doc.earnings) - sum(d.amount for d in doc.deductions)

#     labour_rate = net / 30
#     overtime_rate = labour_rate / 8

#     return overtime_rate

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
