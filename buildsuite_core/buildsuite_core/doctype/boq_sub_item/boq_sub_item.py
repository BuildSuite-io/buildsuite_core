# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class BOQSubItem(Document):
	def validate(self):
		# Snapshot the rate from the Rate Master when linked (not a live link).
		if self.rate_master:
			self.rate = frappe.db.get_value("Construction Rate Master", self.rate_master, "current_rate") or 0
		self.coefficient = flt(self.qty_per_unit)
		self.amount = flt(self.qty_per_unit) * flt(self.rate)

		# Inherit the parent item's WP / cost-head stamps when not explicitly set.
		if self.boq_item and (not self.work_package or not self.cost_head):
			parent = frappe.db.get_value(
				"BOQ Item", self.boq_item, ["work_package", "cost_head"], as_dict=True
			)
			if parent:
				self.work_package = self.work_package or parent.work_package
				self.cost_head = self.cost_head or parent.cost_head
