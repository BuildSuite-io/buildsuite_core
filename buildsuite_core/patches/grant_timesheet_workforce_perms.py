# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Timesheets are entered in the SPA by the roles that keep the Field Attendance muster. Record
permissions are seeded on install only, so existing sites grant the native Timesheet doctype the
same matrix here."""

import frappe

from buildsuite_core.permissions.setup import _SUBMIT_PTYPES, FIELD_ATTENDANCE_ROLE_PERMS, _apply_role_perms


def execute():
	if not frappe.db.exists("DocType", "Timesheet"):
		return
	_apply_role_perms("Timesheet", FIELD_ATTENDANCE_ROLE_PERMS, _SUBMIT_PTYPES)
