# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from buildsuite_core.buildsuite_core.doctype.boq.boq_rollup import recompute_boq

_QUANTITY_SOURCES = ("Manual", "Assembly", "Template", "Takeoff")


def roll_up_item_rate(item_name):
	"""Recompute an assembly item's rate as the sum of its sub-items' per-unit
	amounts, refresh its planned/actual amounts, and roll the BOQ totals.

	Called from the BOQ Sub Item controller whenever a component is added, edited
	or removed, so the parent item's rate always reflects its current components.
	No-op during batch operations (explode / recalc set `boq_skip_rollup` and
	recompute once at the end) or if the item is gone (mid-delete of the parent)."""
	if frappe.flags.get("boq_skip_rollup"):
		return
	item = frappe.db.get_value(
		"BOQ Item", item_name, ["planned_qty", "actual_qty", "boq"], as_dict=True
	)
	if not item:
		return
	rate = sum(
		flt(a)
		for a in frappe.get_all("BOQ Sub Item", filters={"boq_item": item_name}, pluck="amount")
	)
	frappe.db.set_value(
		"BOQ Item",
		item_name,
		{
			"rate": rate,
			"planned_amount": flt(item.planned_qty) * rate,
			"actual_amount": flt(item.actual_qty) * rate,
		},
		update_modified=True,
	)
	recompute_boq(item.boq)


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
		# Flag so the sub-items' delete rollup doesn't re-save this item mid-delete —
		# we recompute the BOQ once below instead.
		frappe.flags.boq_item_deleting = self.name
		try:
			for sub in frappe.get_all("BOQ Sub Item", filters={"boq_item": self.name}, pluck="name"):
				frappe.delete_doc("BOQ Sub Item", sub, force=True, ignore_permissions=True)
		finally:
			frappe.flags.boq_item_deleting = None
		recompute_boq(self.boq)
