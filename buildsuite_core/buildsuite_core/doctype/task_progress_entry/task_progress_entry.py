# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TaskProgressEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		blocker: DF.Check
		blocker_detail: DF.SmallText | None
		cumulative_progress: DF.Float
		entry_date: DF.Date
		narrative: DF.SmallText | None
		skilled_labour: DF.Int
		task: DF.Link
		unskilled_labour: DF.Int
		weather: DF.Literal["", "Clear", "Rainy", "Hot", "Cold", "Storm"]
	# end: auto-generated types

	pass
