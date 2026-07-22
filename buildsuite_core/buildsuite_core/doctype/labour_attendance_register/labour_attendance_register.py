# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import *
from frappe import _
from frappe.utils import flt, getdate

class LabourAttendanceRegister(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		attendance_date: DF.Date
		comments: DF.SmallText | None
		company: DF.Link | None
		daily_wage_calculated: DF.Currency
		employee: DF.Link
		employee_name: DF.Data | None
		field_attendance: DF.Link | None
		naming_series: DF.Literal["LAB-ATT-.YYYY.-"]
		project: DF.Link
		project_name: DF.Data | None
		status: DF.Literal["", "Full Day", "Half Day", "Absent"]
		wage_rate: DF.Currency
	# end: auto-generated types

	def before_save(self):
		self.wage_rate = get_employee_rates(self.employee, self.attendance_date)
	
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


def get_employee_rates(emp, date):
	"""`emp` is a dict from get_employee_map(), not an employee id."""
	emp = frappe.get_doc("Employee",emp)
	wage_rates = (flt(emp.custom_wage))

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


	return labour_rate

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

