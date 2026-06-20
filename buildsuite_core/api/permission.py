import frappe
from frappe import _

from buildsuite_core.permissions.setup import BUILDSUITE_ROLES

# Roles permitted to open the BuildSuite Core app. System Manager is always allowed;
# the BuildSuite personas are sourced from the permission seed to avoid drift.
ALLOWED_ROLES = {"System Manager", *BUILDSUITE_ROLES}


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


# The SPA probes access on boot before login; returns only a guest-safe
# {allowed: False} for unauthenticated users.
@frappe.whitelist(methods=["GET"], allow_guest=True)  # nosemgrep
def get_access_context():
	user = frappe.session.user
	if user == "Guest":
		return frappe._dict({"allowed": False, "user": user, "roles": [], "reason": "guest"})

	roles = list(frappe.get_roles())
	allowed = _has_app_permission(log_denial=False)
	reason = "ok" if allowed else "missing_role"

	# Persona (User.persona Select) is the single source of truth for the user's
	# BuildSuite role; the frontend uses it to set the active persona on load.
	persona = frappe.db.get_value("User", user, "persona") if user != "Guest" else None

	return frappe._dict(
		{
			"allowed": allowed,
			"user": user,
			"roles": roles,
			"persona": persona,
			"reason": reason,
		}
	)
