"""Remove the self-service Employee User Permission from roster-managing users.

ERPNext auto-creates a User Permission (allow=Employee, own record) when a user is linked to their
Employee. For a user who manages the roster (an Employee-write BuildSuite role) that restriction
contradicts the permission matrix — it hides every OTHER employee (empty field-employee list, 403
on read). Going forward the User Permission after_insert hook drops it; this converges existing
sites by removing the ones already there.
"""

import frappe


def execute():
	from buildsuite_core.utils.employee_permissions import is_roster_manager

	rows = frappe.get_all("User Permission", filters={"allow": "Employee"}, fields=["name", "user"])
	removed = 0
	for r in rows:
		if is_roster_manager(r.user):
			frappe.db.delete("User Permission", {"name": r.name})
			removed += 1

	if removed:
		frappe.clear_cache()
	print(f"drop_manager_employee_user_permissions: removed {removed} self-service Employee perms")
