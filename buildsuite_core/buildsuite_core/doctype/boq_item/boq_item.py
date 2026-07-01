# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
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
		self._validate_project_scope()

	def _validate_project_scope(self):
		"""A BOQ Item's Task and Work Package must belong to the BOQ's own project —
		you can't cost work from another project into this BOQ."""
		if not (self.task or self.work_package):
			return
		boq_project = frappe.db.get_value("BOQ", self.boq, "project")
		if not boq_project:
			return
		if self.task:
			task_project = frappe.db.get_value("Task", self.task, "project")
			if task_project and task_project != boq_project:
				frappe.throw(
					_("Task {0} belongs to project {1}, not this BOQ's project {2}.").format(
						self.task, task_project, boq_project
					)
				)
		if self.work_package:
			wp_project = frappe.db.get_value("Work Package", self.work_package, "project")
			if wp_project and wp_project != boq_project:
				frappe.throw(
					_("Work Package {0} belongs to project {1}, not this BOQ's project {2}.").format(
						self.work_package, wp_project, boq_project
					)
				)

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
