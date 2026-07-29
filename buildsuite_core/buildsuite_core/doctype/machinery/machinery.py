# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Machinery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		asset: DF.Link | None
		company: DF.Link
		machinery_code: DF.Data
		machinery_name: DF.Data
		machinery_type: DF.Link
		owner_vendor: DF.Data | None
		ownership: DF.Literal["Owned", "Hired"]
		rate: DF.Currency
		rate_unit: DF.Literal["Hour", "Day", "Month"]
		status: DF.Literal["Active", "Inactive"]
	# end: auto-generated types

	pass
