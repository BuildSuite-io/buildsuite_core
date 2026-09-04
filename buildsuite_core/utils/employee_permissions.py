# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Keep roster-managing users out of ERPNext's self-service Employee restriction.

When a User is linked to an Employee (``user_id`` set), ERPNext auto-creates a User Permission
(``allow=Employee``, ``for_value=<that employee>``) so a regular employee only ever sees their OWN
record — leave, payslip, and so on. For a user who MANAGES the roster (holds a BuildSuite
Employee-write role: HR Manager / PM / Site Engineer / Administrator), that restriction directly
contradicts the permission matrix — it stops them reading or LISTING other employees, so the
field-employee list comes back empty and opening any other worker 403s.

We drop the restriction for those users, so their Employee access matches the matrix (full CRUD).
ERPNext re-creates the permission whenever the Employee is saved, so the ``after_insert`` hook fires
each time and keeps it gone. It only ever touches the auto-created self-service Employee permission;
Company (and any other) user permissions are left untouched.
"""

import frappe

from buildsuite_core.permissions.setup import EMPLOYEE_WRITE_ROLE_PERMS

# Holders of these roles manage the employee roster — the self-service restriction must not apply.
ROSTER_ROLES = frozenset(EMPLOYEE_WRITE_ROLE_PERMS)


def is_roster_manager(user: str) -> bool:
	return bool(user and ROSTER_ROLES & set(frappe.get_roles(user)))


def drop_self_service_for_managers(doc, method=None):
	"""User Permission ``after_insert`` hook — remove a self-service Employee permission the moment
	it is created for a roster-managing user."""
	if doc.allow != "Employee" or not doc.user:
		return
	if is_roster_manager(doc.user):
		frappe.db.delete("User Permission", {"name": doc.name})
		frappe.clear_cache(user=doc.user)
