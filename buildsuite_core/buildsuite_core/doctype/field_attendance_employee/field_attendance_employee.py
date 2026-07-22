# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FieldAttendanceEmployee(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		comments: DF.SmallText | None
		employee: DF.Link
		employee_name: DF.Data | None
		labour_rate: DF.Currency
		overtime_hours: DF.Float
		overtime_rate: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal["", "Present", "Half Day", "Absent", "Overtime Only"]
	# end: auto-generated types

	pass
