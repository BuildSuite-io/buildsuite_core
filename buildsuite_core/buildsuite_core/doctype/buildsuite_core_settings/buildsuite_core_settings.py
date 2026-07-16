# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BuildSuiteCoreSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		project_naming: DF.Literal["Project ID", "Name Series"]
		rate_master_update_threshold: DF.Percent
	# end: auto-generated types

	pass
