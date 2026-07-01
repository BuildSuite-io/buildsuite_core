# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BOQGroup(Document):
	def on_trash(self):
		# Cascade-delete this group's items (which cascade to their sub-items).
		for item in frappe.get_all("BOQ Item", filters={"boq_group": self.name}, pluck="name"):
			frappe.delete_doc("BOQ Item", item, force=True, ignore_permissions=True)
