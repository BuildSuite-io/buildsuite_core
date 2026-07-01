# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EstimateTemplateRow(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		assembly: DF.Link | None
		cost_head: DF.Literal["Material", "Labour", "Equipment", "Subcontract", "Overhead"]
		description: DF.Data | None
		group_name: DF.Data
		line_type: DF.Literal["Assembly", "Resource"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		placeholder_qty: DF.Float
		rate: DF.Currency
		resource: DF.Link | None
		uom: DF.Link | None
	# end: auto-generated types

	pass
