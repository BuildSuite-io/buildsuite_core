# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _


def revert_task_on_tpe_delete(tpe):
	"""Rebuild the task's progress detail rows from the remaining TPEs after a delete.

	Called from TaskProgressEntry.on_trash. on_trash fires before the row leaves the
	DB, so we exclude the deleted TPE by name and rebuild task_progress_details from
	whatever survives — robust against duplicate (date, user, progress) tuples that a
	fuzzy match would mishandle. Progress is the max cumulative of the survivors;
	saving the task fires the status sync, so dropping to 0% reverts to Yet To Start.
	"""
	if not tpe.task or not frappe.db.exists("Task", tpe.task):
		return

	# The parent task is itself being cascade-deleted — recomputing its progress
	# is pointless and would save a doc that's about to be removed.
	if frappe.flags.get("buildsuite_deleting_task") == tpe.task:
		return

	remaining = frappe.get_all(
		"Task Progress Entry",
		filters={"task": tpe.task, "name": ("!=", tpe.name)},
		fields=["entry_date", "cumulative_progress", "owner"],
		order_by="entry_date asc, creation asc",
	)

	task = frappe.get_doc("Task", tpe.task)
	task.set("task_progress_details", [])
	for row in remaining:
		task.append(
			"task_progress_details",
			{
				"date": row.entry_date,
				"cumulative_progress": row.cumulative_progress,
				"user": row.owner,
			},
		)

	task.progress = max((flt(row.cumulative_progress or 0) for row in remaining), default=0)

	# Also clear the native ERPNext status: erpnext Task.validate_progress forces
	# progress back to 100 whenever status == "Completed", and it runs before our
	# status-sync hook. So a task left "Completed" by the deleted entry would snap
	# back to 100 unless we drop it off Completed here first.
	if flt(task.progress) <= 0:
		task.task_status = "Yet To Start"
		task.status = "Open"
	elif flt(task.progress) < 100:
		if task.task_status == "Completed":
			task.task_status = "In Progress"
		if task.status == "Completed":
			task.status = "Working"

	task.save(ignore_permissions=True)



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

	def validate(self):
		# Blocker flag requires a note. Server-side so the rule holds on both the
		# File-Progress-Entry dialog and the TPE edit screen (the dialog enforces it
		# client-side; the edit screen previously bypassed it).
		if self.blocker and not (self.blocker_detail or "").strip():
			frappe.throw(_("A blocker note is required when the blocker flag is set."))

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

		# Drive the BuildSuite task_status; the Task validate hook
		# (buildsuite_core.utils.task.update_task_status) maps it onto the native
		# ERPNext status field and rolls up project progress. We must NOT set
		# project.status to "Working" here — that's not a valid ERPNext Project
		# status value and throws on save.
		if task.progress >= 100:
			task.task_status = "Completed"
		elif task.task_status in (None, "", "Yet To Start"):
			task.task_status = "In Progress"
		task.save(ignore_permissions=True)

	def on_trash(self):
		# Reverting on delete: drop this entry's detail row from the parent task,
		# recompute progress from the remaining rows, and let the status sync flip
		# the task back (0% -> Yet To Start). Mirrors the prototype recompute.
		revert_task_on_tpe_delete(self)
