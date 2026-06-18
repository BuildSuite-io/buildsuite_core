# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Assembly(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.assembly_component.assembly_component import AssemblyComponent
		from frappe.types import DF

		assembly_code: DF.Data
		assembly_name: DF.Data
		category: DF.Literal["Concrete", "Masonry", "Reinforcement", "Finishing", "General"]
		components: DF.Table[AssemblyComponent]
		disabled: DF.Check
		notes: DF.SmallText | None
		rate_per_unit: DF.Currency
		uom: DF.Link
	# end: auto-generated types

	def validate(self):
		total = 0
		for c in self.components:
			c.rate = frappe.db.get_value("Construction Rate Master", c.resource, "current_rate") or 0
			c.amount = (c.coefficient or 0) * c.rate
			total += c.amount
		self.rate_per_unit = total
