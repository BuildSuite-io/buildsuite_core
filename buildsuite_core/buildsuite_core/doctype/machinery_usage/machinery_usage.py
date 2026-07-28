# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MachineryUsage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		fuel_cost: DF.Currency
		machine: DF.Link
		project: DF.Link | None
		quantity: DF.Float
		rate: DF.Currency
		task: DF.Link | None
		unit: DF.Literal["Days", "Hours"]
	# end: auto-generated types

	pass
