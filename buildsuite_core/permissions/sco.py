"""Record-level access for the Scope Change Order doctype.

The SCO role matrix (setup.py SCO_ROLE_PERMS) is flat — full roles (Director, PM,
QS, Administrator, System Manager) and the read-only roles (Estimator, Procurement
Officer, Accountant) see every change order. The **Site Engineer** is the one scoped
role: they can *raise* (create) a change order and read only their OWN, and cannot
approve (approval is gated to BOQ_APPROVE_ROLES in api/sco.py). Foreman / Store Keeper
/ HR Manager have no DocPerm at all, so they never reach these hooks.
"""

import frappe

# Roles restricted to their own change orders.
OWN_SCOPE_ROLES = {"BuildSuite Site Engineer"}

# Roles that grant the broader "see everything" access; a user holding any of these
# is NOT own-scoped even if they also hold an own-scope role.
_BROADER_ROLES = {
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite QS",
	"BuildSuite Administrator",
	"System Manager",
	"BuildSuite Estimator",
	"BuildSuite Procurement Officer",
	"BuildSuite Accountant",
}


def _is_own_scoped(user):
	roles = set(frappe.get_roles(user))
	return bool(roles & OWN_SCOPE_ROLES) and not (roles & _BROADER_ROLES)


def get_sco_permission_query(user):
	"""List-view scoping: own-scoped users see only change orders they created."""
	if not user:
		user = frappe.session.user
	if _is_own_scoped(user):
		return f"(`tabScope Change Order`.owner = {frappe.db.escape(user)})"
	return ""


def has_sco_permission(doc, ptype="read", user=None):
	"""Record-level gate: own-scoped users may create freely but only act on their
	own change orders. Everyone else is governed purely by DocPerm."""
	if not user:
		user = frappe.session.user
	if not _is_own_scoped(user):
		return True
	if ptype == "create":
		return True
	if not getattr(doc, "name", None):
		return True
	return doc.owner == user
