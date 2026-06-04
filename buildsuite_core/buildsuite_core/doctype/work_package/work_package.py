# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkPackage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		budget: DF.Currency
		code: DF.Data | None
		description: DF.Text | None
		end_date: DF.Date | None
		owner_user: DF.Link | None
		progress: DF.Percent
		project: DF.Link
		start_date: DF.Date | None
		status: DF.Literal["Planned", "In Progress", "On Hold", "Completed"]
		work_package_name: DF.Data
	# end: auto-generated types

	pass
