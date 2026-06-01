import frappe
from frappe import _

ALLOWED_ROLES = {
	"System Manager",
}


def has_app_permission() -> bool:
	return _has_app_permission(log_denial=True)


def _has_app_permission(log_denial: bool = True) -> bool:
	if frappe.session.user == "Guest":
		return False

	roles = set(frappe.get_roles())
	if roles.intersection(ALLOWED_ROLES):
		return True

	if log_denial:
		frappe.log_error(
			title="BuildSuite Core access denied",
			message=_(
				"User {0} attempted to access BuildSuite Core without an allowed role.",
				[frappe.session.user],
			),
		)
	return False


@frappe.whitelist(methods=["GET"], allow_guest=True)
def get_access_context():
	user = frappe.session.user
	if user == "Guest":
		return frappe._dict({"allowed": False, "user": user, "roles": [], "reason": "guest"})

	roles = list(frappe.get_roles())
	allowed = _has_app_permission(log_denial=False)
	reason = "ok" if allowed else "missing_role"

	return frappe._dict({
		"allowed": allowed,
		"user": user,
		"roles": roles,
		"reason": reason,
	})
