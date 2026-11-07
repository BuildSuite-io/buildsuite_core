# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""How many hours make a full day of labour.

A full day is not always 8 hours: some companies work 9 or 10 and count anything beyond as
overtime, and a project can differ from its company. This module is the ONLY place a number of
hours per day is written down; everything that costs or counts labour asks get_full_day_hours():

	project.full_day_hours  ->  company.full_day_hours  ->  DEFAULT_FULL_DAY_HOURS

Mirrors frontend/src/utils/fullDay.js.
"""

import frappe
from frappe import _
from frappe.utils import flt

# The fallback when neither the project nor the company says. The one literal 8 in workforce code.
DEFAULT_FULL_DAY_HOURS = 8

MAX_FULL_DAY_HOURS = 24


def is_valid_full_day_hours(value) -> bool:
	"""A usable full day: more than 0 and no more than 24."""
	return value not in (None, "") and 0 < flt(value) <= MAX_FULL_DAY_HOURS


def validate_full_day_hours(value) -> None:
	"""Throw the one message every form shows for a bad value."""
	if not is_valid_full_day_hours(value):
		frappe.throw(_("Full day hours must be more than 0 and no more than 24."))


def get_full_day_hours(project: str | None = None, company: str | None = None) -> float:
	"""The hours in a full day for this project / company: the project's own value, else the
	company's, else the default. Read straight from the database so a user who may not read the
	company's permlevel-protected field still gets the real value."""
	if project:
		own = frappe.db.get_value("Project", project, "full_day_hours")
		if is_valid_full_day_hours(own):
			return flt(own)
		company = company or frappe.db.get_value("Project", project, "company")
	if company:
		theirs = frappe.db.get_value("Company", company, "full_day_hours")
		if is_valid_full_day_hours(theirs):
			return flt(theirs)
	return DEFAULT_FULL_DAY_HOURS


# --- doc_events ------------------------------------------------------------------------------

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}


def validate_company_full_day_hours(doc, method=None):
	"""Company: required (a blank is refused by the field itself) and within (0, 24]. A brand-new
	company with no value takes the default, as the field's own default would for a form."""
	if doc.is_new() and doc.get("full_day_hours") in (None, ""):
		doc.full_day_hours = DEFAULT_FULL_DAY_HOURS
	if doc.get("full_day_hours") not in (None, ""):
		validate_full_day_hours(doc.full_day_hours)


def validate_project_full_day_hours(doc, method=None):
	"""Project: optional (blank = the company's value), no more than 24 and never negative, and only
	changeable by a System Manager, a BuildSuite Administrator or the project's own Project Manager.
	That last rule is per-record, so it lives here rather than in a permlevel.

	A Float can't be NULL in the database, so a blank project value is stored as 0 and read back as
	0: on a Project, 0 means "not set" (unlike Company, where the field is required and 0 is refused)."""
	if flt(doc.get("full_day_hours")):
		validate_full_day_hours(doc.full_day_hours)

	if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate:
		return
	if not _full_day_changed(doc):
		return
	if not can_edit_project_full_day(doc):
		frappe.throw(
			_(
				"Only a System Manager, a BuildSuite Administrator or this project's Project Manager can set the full day hours."
			),
			frappe.PermissionError,
		)


def _full_day_changed(doc) -> bool:
	if doc.is_new():
		return doc.get("full_day_hours") not in (None, "")
	before = doc.get_doc_before_save()
	return flt(before.get("full_day_hours") if before else None) != flt(doc.get("full_day_hours"))


def can_edit_project_full_day(doc, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if ADMIN_ROLES & set(frappe.get_roles(user)):
		return True
	# The project's own PM: the stored one for an existing project, so a user can't make
	# themselves PM and set the hours in the same save.
	before = None if doc.is_new() else doc.get_doc_before_save()
	pm = (before.get("project_manager") if before else None) or (
		doc.get("project_manager") if doc.is_new() else None
	)
	return bool(pm) and pm == user
