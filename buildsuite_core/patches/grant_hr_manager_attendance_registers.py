"""BuildSuite HR Manager may create and delete Labour / Overtime Attendance Registers.

Additive only. HR Manager's existing rule on each register gains create and delete; every other
flag on it, and every other role's rule, is left exactly as the site has it. A site with no HR
Manager rule there gets the shipped default (read + create + delete).
"""

import frappe

REGISTERS = ("Labour Attendance Register", "Overtime Attendance Register")
ROLE = "BuildSuite HR Manager"


def execute():
	from frappe.permissions import update_permission_property

	from buildsuite_core.permissions.setup import (
		_SUBMIT_PTYPES,
		DERIVED_ATTENDANCE_ROLE_PERMS,
		HR_ATTENDANCE_REGISTER_PERMS,
		_grant_missing_role_perms,
	)

	if not frappe.db.exists("Role", ROLE):
		return
	for doctype in REGISTERS:
		if not frappe.db.exists("DocType", doctype):
			continue
		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": ROLE, "permlevel": 0}):
			for ptype, value in HR_ATTENDANCE_REGISTER_PERMS.items():
				update_permission_property(doctype, ROLE, 0, ptype, value, validate=False)
		else:
			_grant_missing_role_perms(doctype, {ROLE: DERIVED_ATTENDANCE_ROLE_PERMS[ROLE]}, _SUBMIT_PTYPES)
	frappe.clear_cache()
