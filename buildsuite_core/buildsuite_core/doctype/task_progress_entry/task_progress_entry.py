# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _



class TaskProgressEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		blocker: DF.Check
		blocker_detail: DF.SmallText | None
		cumulative_progress: DF.Float
		entry_date: DF.Date
		narrative: DF.SmallText | None
		skilled: DF.Int
		task: DF.Link
		unskilled: DF.Int
		weather: DF.Literal["", "Clear", "Rainy", "Hot", "Cold", "Storm"]
	# end: auto-generated types

	def before_save(self):
		task = frappe.get_doc("Task", self.task)

		if self.is_new():
			duplicate = False

			for row in task.get("task_progress_details") or []:
				if (
					row.date == self.entry_date
					and row.user == self.owner
					and abs(
						flt(row.cumulative_progress or 0)
						- flt(self.cumulative_progress or 0)
					) < 0.001
				):
					duplicate = True
					break

			if not duplicate:
				task.append(
					"task_progress_details",
					{
						"date": self.entry_date,
						"cumulative_progress": self.cumulative_progress,
						"user": self.owner,
					},
				)

		task.progress = max(
			(
				flt(row.cumulative_progress or 0)
				for row in task.get("task_progress_details") or []
			),
			default=0,
		)

		if task.progress > 100:
			frappe.throw(_("Cumulative progress cannot exceed 100%"))

		task.save(ignore_permissions=True)
	pass
