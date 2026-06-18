# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Whitelisted helpers to manage a Task's assignee.

BuildSuite treats "Assignee" as Frappe's native assignment (the ToDo-backed
`_assign` field) so it stays consistent with the record-level Task permissions
(a Foreman may act on tasks assigned to them via `_assign`). The UI presents a
SINGLE assignee, so set_task_assignee clears any existing assignment before
assigning the new user — there is never more than one.
"""

import frappe
from frappe.desk.form.assign_to import add as _assign_add, clear as _assign_clear


def _current_assignee(task):
	rows = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": "Task",
			"reference_name": task,
			"status": ("!=", "Cancelled"),
		},
		pluck="allocated_to",
	)
	return rows[0] if rows else None


@frappe.whitelist()
def get_task_assignee(task):
	return _current_assignee(task)


@frappe.whitelist()
def set_task_assignee(task, assignee=None):
	"""Single-assignee model on top of `_assign`: drop whatever was assigned
	before, then assign the given user (if any). Returns the resulting assignee."""
	frappe.get_doc("Task", task).check_permission("write")

	assignee = (assignee or "").strip() or None
	if _current_assignee(task) == assignee:
		return assignee

	# Single assignee — remove every prior assignment before adding the new one.
	# Mute messages so assign_to's benign "Shared with the following Users…"
	# msgprint (emitted over realtime) doesn't surface in the UI as an error.
	mute = frappe.flags.mute_messages
	frappe.flags.mute_messages = True
	try:
		_assign_clear("Task", task)
		if assignee:
			_assign_add({"doctype": "Task", "name": task, "assign_to": [assignee]})
	finally:
		frappe.flags.mute_messages = mute

	return assignee
