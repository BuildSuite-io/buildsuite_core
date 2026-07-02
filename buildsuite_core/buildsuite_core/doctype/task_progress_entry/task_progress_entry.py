# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


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
		# A task can't log progress while a Finish-to-Start predecessor is still open.
		self._block_if_predecessor_incomplete()
		self._reject_if_task_completed()

		# Blocker flag requires a note. Server-side so the rule holds on both the
		# File-Progress-Entry dialog and the TPE edit screen (the dialog enforces it
		# client-side; the edit screen previously bypassed it).
		if self.blocker and not (self.blocker_detail or "").strip():
			frappe.throw(_("A blocker note is required when the blocker flag is set."))

		self._reject_noop_edit()
		self._validate_monotonic_progress()

	def _block_if_predecessor_incomplete(self):
		from buildsuite_core.api.schedule import incomplete_fs_predecessor

		pred = incomplete_fs_predecessor(self.task)
		if pred:
			frappe.throw(
				_(
					"You can't log progress on this task yet — its Finish-to-Start "
					'predecessor "{0}" isn\'t Completed.'
				).format(pred)
			)

	def _reject_if_task_completed(self):
		# A completed task takes no further progress entries. Guards NEW entries only
		# (editing the entry that completed the task must still be allowed). Enforced
		# in the controller so it holds from the form, the TPE list, and the API alike.
		if not self.is_new():
			return
		task = frappe.db.get_value("Task", self.task, ["task_status", "progress"], as_dict=True)
		if task and (task.task_status == "Completed" or flt(task.progress) >= 100):
			frappe.throw(
				_("Task {0} is already Completed — no further progress entries can be added.").format(
					self.task
				)
			)

	# Fields a user can change on a progress entry; if none differ from the stored
	# row, the save is a no-op and must be blocked (not logged as a duplicate).
	_TRACKED_FIELDS = (
		"cumulative_progress",
		"entry_date",
		"narrative",
		"weather",
		"skilled",
		"unskilled",
		"blocker",
		"blocker_detail",
	)

	def _reject_noop_edit(self):
		# Editing an entry and saving without changing anything must NOT persist. New
		# entries are covered by the strict-increase rule below.
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before:
			return
		if all(self.get(f) == before.get(f) for f in self._TRACKED_FIELDS):
			frappe.throw(_("No changes made — there's nothing to save."))

	def _validate_monotonic_progress(self):
		# Progress is cumulative and strictly monotonic: every entry must record MORE
		# progress than the task already has. So an entry can't be 0%, can't repeat the
		# current value (a no-op duplicate), can't go backwards, and can't exceed 100%.
		# Reject (throw) so nothing is persisted, rather than logging a dead row.
		value = flt(self.cumulative_progress or 0)
		if value > 100:
			frappe.throw(_("Cumulative progress can't exceed 100%."))
		if value <= 0:
			frappe.throw(_("A progress entry can't be 0% — record the progress actually made."))

		# Floor = highest cumulative already recorded on the task by any OTHER entry
		# (exclude this row when editing; a brand-new row excludes nothing).
		filters = {"task": self.task}
		if not self.is_new():
			filters["name"] = ("!=", self.name)
		floor = max(
			(
				flt(x)
				for x in frappe.get_all("Task Progress Entry", filters=filters, pluck="cumulative_progress")
			),
			default=0,
		)
		label = floor if floor % 1 else int(floor)
		if abs(value - floor) < 0.001:
			frappe.throw(
				_(
					"No changes made — {0}% is already the task's current progress. "
					"A progress entry has to increase it."
				).format(label)
			)
		if value < floor:
			frappe.throw(
				_(
					"Progress can't go backwards — {0}% is below the task's current progress ({1}%). "
					"Progress entries are cumulative and can only increase."
				).format(value if value % 1 else int(value), label)
			)

	def before_save(self):
		task = frappe.get_doc("Task", self.task)
		if self.is_new():
			task.append(
				"task_progress_details",
				{
					"date": self.entry_date,
					"cumulative_progress": self.cumulative_progress,
					"user": self.owner,
				},
			)

		task.progress = max(
			(flt(row.cumulative_progress or 0) for row in task.get("task_progress_details") or []),
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
