# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
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
	# end: auto-generated types

	pass
