# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ConstructionRateHistory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		changed_by: DF.Link | None
		changed_on: DF.Datetime | None
		effective_from: DF.Date | None
		effective_to: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purchase_order: DF.Link | None
		rate: DF.Currency
		reason: DF.Literal[
			"", "Initial", "Manual revision", "Purchase-driven", "Market revision", "Supplier quote"
		]
		remarks: DF.SmallText | None
		supplier: DF.Link | None
	# end: auto-generated types

	pass
