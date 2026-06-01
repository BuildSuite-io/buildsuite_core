import frappe
from frappe import _

ALLOWED_ROLES = {
	"System Manager",
}


def has_app_permission() -> bool:
	if frappe.session.user == "Guest":
		return False

	roles = set(frappe.get_roles())
	if roles.intersection(ALLOWED_ROLES):
		return True

	frappe.log_error(
		title="BuildSuite Core access denied",
		message=_(
			"User {0} attempted to access BuildSuite Core without an allowed role.",
			[frappe.session.user],
		),
	)
	return False
