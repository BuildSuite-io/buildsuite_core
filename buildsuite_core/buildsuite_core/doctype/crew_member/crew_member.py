# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CrewMember(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		daily_rate: DF.Currency
		field_employee: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		role_in_crew: DF.Link | None
	# end: auto-generated types

	pass
