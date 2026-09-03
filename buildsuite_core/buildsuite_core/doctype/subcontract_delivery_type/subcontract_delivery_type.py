# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from buildsuite_core.utils.project import default_company


class SubcontractDeliveryType(Document):
	def before_insert(self):
		if not self.company:
			self.company = default_company()
