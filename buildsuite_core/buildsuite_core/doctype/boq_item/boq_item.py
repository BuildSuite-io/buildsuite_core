# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from buildsuite_core.buildsuite_core.doctype.boq.boq_rollup import recompute_boq

_QUANTITY_SOURCES = ("Manual", "Assembly", "Template", "Takeoff")


class BOQItem(Document):
	def validate(self):
		self.planned_amount = flt(self.planned_qty) * flt(self.rate)
		self.actual_amount = flt(self.actual_qty) * flt(self.rate)
		if not self.driving_qty:
			self.driving_qty = self.planned_qty
		if self.quantity_source not in _QUANTITY_SOURCES:
			self.quantity_source = "Manual"

	def on_update(self):
		# Propagate WP / cost-head stamps to child sub-items (denormalized join keys).
		frappe.db.set_value(
			"BOQ Sub Item",
			{"boq_item": self.name},
			{"work_package": self.work_package, "cost_head": self.cost_head},
			update_modified=False,
		)
		recompute_boq(self.boq)

	def on_trash(self):
		for sub in frappe.get_all("BOQ Sub Item", filters={"boq_item": self.name}, pluck="name"):
			frappe.delete_doc("BOQ Sub Item", sub, force=True, ignore_permissions=True)
		recompute_boq(self.boq)
