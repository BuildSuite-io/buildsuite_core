# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class RateMasterCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Data | None
		resource_type: DF.Literal["Material", "Labour", "Equipment"]
	# end: auto-generated types

	pass
