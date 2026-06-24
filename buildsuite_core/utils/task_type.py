# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from buildsuite_core.utils.task import _TASK_TYPE_VALUES


def protect_core_task_types(doc, method=None):
	"""Block deletion of the scheduling-critical Task Types.

	Admins may freely add and delete their own Task Types, but the frontend
	scheduling engine keys special behaviour off the names "Milestone" (single-date
	diamond) and "Inspection" (downstream gate); "Activity" is the default every task
	falls back to. Deleting any of these would break the Gantt — so guard them.
	"""
	if doc.name in _TASK_TYPE_VALUES:
		frappe.throw(
			_("{0} is a core Task Type used by the scheduler and cannot be deleted.").format(doc.name)
		)
