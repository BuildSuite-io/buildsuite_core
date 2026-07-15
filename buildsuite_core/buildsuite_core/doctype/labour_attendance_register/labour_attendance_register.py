# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import *
from frappe import _

class LabourAttendanceRegister(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		attendance_date: DF.Date
		company: DF.Link | None
		daily_wage_calculated: DF.Currency
		day_type: DF.Literal["", "Regular", "Off Day"]
		employee: DF.Link
		employee_name: DF.Data | None
		naming_series: DF.Literal["LAB-ATT-.YYYY.-"]
		project: DF.Link
		project_name: DF.Data | None
		status: DF.Literal["", "Full Day", "Half Day", "Absent"]
		wage_rate: DF.Currency
	# end: auto-generated types

	def before_save(self):
		self.wage_rate = frappe.db.get_value("Employee", self.employee, "custom_wage") or 0
	
	def validate(self):
		self.validate_status()
		self.update_daily_wages()

	def update_daily_wages(self):

		if self.status == "Full Day":
			self.daily_wage_calculated = self.wage_rate
		if self.status == "Half Day":
			self.daily_wage_calculated = self.wage_rate/2
		if self.status == "Absent":
			self.daily_wage_calculated = 0
	
	def validate_status(self):
		docs = [x.get("status") for x in frappe.get_all("Labour Attendance Register",{"attendance_date":self.attendance_date,"docstatus":1,"employee":self.employee},["status"])]
		if docs:
			if self.status == "Full Day" or self.status == "Absent":
				if "Full Day" in docs or "Half Day" in docs or "Absent" in docs:
					frappe.throw(f"Cannot Mark {frappe.bold(self.status)} for Employee {frappe.bold(self.employee)} as is Already Marked {docs[0]}.")

			if self.status == "Half Day":
				if "Full Day" in docs or "Absent" in docs:
					frappe.throw(f"Cannot Mark {frappe.bold(self.status)} for Employee {frappe.bold(self.employee)} as is Already Marked {docs[0]}.")


			if docs.count("Half Day") == 2 and self.status in ["Half Day", "Full Day", "Absent"]:
				frappe.throw(f"Cannot Mark {frappe.bold(self.status)} for Employee {frappe.bold(self.employee)} as 2 Half Days are Marked Already!")


# def get_employee_rates(employee, date):
#     # Returns the daily labour rate as a scalar. The non-salaried branch used
#     # to return a (wage, ot_wage) tuple, which was assigned straight to the
#     # Currency field `wage_rate` in before_save — that broke save_version's
#     # diff formatter (fmt_money does `amount % 1` and a tuple raises TypeError).
#     if frappe.db.get_value("Employee", employee, "custom_labour_wage_type") != "Salaried":
#         return frappe.db.get_value("Employee", employee, "custom_wage") or 0

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

#     return labour_rate

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

@frappe.whitelist()
def project_list_query(doctype, txt, searchfield, start, page_len, filters):
	if filters:
		query = """
			SELECT
				pro.name as name,
				pro.project_name
			FROM
				`tabProject` as pro,
				`tabEmployee` as emp,
				`tabProject Assigned` as pa
			WHERE
				emp.name = %(employee)s AND
				emp.name = pa.parent AND
				pa.project = pro.name
			GROUP BY
				pro.name
			LIMIT %(start)s, %(page_len)s
		"""
		values = frappe.db.sql(query.format(**{
			}), {
			'employee': filters['employee'],
			'txt': "%{}%".format(txt),
			'start': start,
			'page_len': page_len
		})
		return values

