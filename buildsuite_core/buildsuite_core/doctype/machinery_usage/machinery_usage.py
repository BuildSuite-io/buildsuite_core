# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MachineryUsage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		fuel_cost: DF.Currency
		machine: DF.Link
		project: DF.Link | None
		quantity: DF.Float
		rate: DF.Currency
		task: DF.Link | None
		unit: DF.Literal["Days", "Hours"]
	# end: auto-generated types

	def validate(self):
		# The task is optional, but if set it must belong to the selected project —
		# a usage log must never be booked against a task from another project.
		if self.task and self.project:
			task_project = frappe.db.get_value("Task", self.task, "project")
			if task_project != self.project:
				frappe.throw(_("Task {0} does not belong to project {1}.").format(self.task, self.project))
