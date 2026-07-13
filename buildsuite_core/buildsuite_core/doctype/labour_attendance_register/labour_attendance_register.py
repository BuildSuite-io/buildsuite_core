# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


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

	pass
