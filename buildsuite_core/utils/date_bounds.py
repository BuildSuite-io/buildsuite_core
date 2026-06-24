# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Hierarchy date-boundary validation.

A record's schedule must sit inside its parent's:
  * Task / Work Package / Stage Planning dates must fall within their Project's
    expected_start_date .. expected_end_date.
  * A sub-project's dates must fall within its parent Project's dates.
  * On every record, the end date may not precede the start date.

All checks are skipped for any boundary the parent (or the record) leaves blank,
and each rejection names the conflicting parent boundary so the message is clear.
Wired via doc_events `validate` in hooks.py, so it guards both create and edit.
"""

import frappe
from frappe import _
from frappe.utils import formatdate, getdate


def _check_end_after_start(start, end):
	if start and end and getdate(end) < getdate(start):
		frappe.throw(
			_("End date ({0}) can't be earlier than the start date ({1}).").format(
				formatdate(end), formatdate(start)
			),
			title=_("Invalid dates"),
		)


def _check_within(start, end, parent_start, parent_end, parent_label):
	if start and parent_start and getdate(start) < getdate(parent_start):
		frappe.throw(
			_("Start date ({0}) can't be before the {1} start date ({2}).").format(
				formatdate(start), parent_label, formatdate(parent_start)
			),
			title=_("Date out of bounds"),
		)
	if end and parent_end and getdate(end) > getdate(parent_end):
		frappe.throw(
			_("End date ({0}) can't be after the {1} end date ({2}).").format(
				formatdate(end), parent_label, formatdate(parent_end)
			),
			title=_("Date out of bounds"),
		)


def _project_bounds(project):
	"""Return (expected_start_date, expected_end_date) for a Project, or (None, None)."""
	if not project:
		return None, None
	row = frappe.db.get_value("Project", project, ["expected_start_date", "expected_end_date"], as_dict=True)
	if not row:
		return None, None
	return row.expected_start_date, row.expected_end_date


def validate_project_dates(doc, method=None):
	"""Project: end >= start, and a sub-project stays within its parent project."""
	_check_end_after_start(doc.expected_start_date, doc.expected_end_date)
	if doc.get("parent_project"):
		p_start, p_end = _project_bounds(doc.parent_project)
		_check_within(doc.expected_start_date, doc.expected_end_date, p_start, p_end, _("parent project"))


def validate_task_dates(doc, method=None):
	"""Task: end >= start, and the task stays within its project."""
	_check_end_after_start(doc.exp_start_date, doc.exp_end_date)
	p_start, p_end = _project_bounds(doc.get("project"))
	_check_within(doc.exp_start_date, doc.exp_end_date, p_start, p_end, _("project"))


def validate_work_package_dates(doc, method=None):
	"""Work Package: end >= start, and the package stays within its project."""
	_check_end_after_start(doc.start_date, doc.end_date)
	p_start, p_end = _project_bounds(doc.get("project"))
	_check_within(doc.start_date, doc.end_date, p_start, p_end, _("project"))


def validate_stage_planning_dates(doc, method=None):
	"""Stage Planning: end >= start, and the stage stays within its project."""
	_check_end_after_start(doc.planned_start, doc.planned_end)
	p_start, p_end = _project_bounds(doc.get("project"))
	_check_within(doc.planned_start, doc.planned_end, p_start, p_end, _("project"))
