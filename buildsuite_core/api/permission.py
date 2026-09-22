import frappe
from frappe import _

from buildsuite_core.permissions.resource_map import RESOURCE_DOCTYPES
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
	# Site-level developer flag (site_config.json) — the frontend uses it to show
	# dev-only affordances like the role switcher.
	developer_mode = bool(frappe.conf.developer_mode)
	if user == "Guest":
		return frappe._dict(
			{
				"allowed": False,
				"user": user,
				"roles": [],
				"reason": "guest",
				"developer_mode": developer_mode,
			}
		)

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
			# Backend-derived UI gating caps, folded into the boot probe so the SPA needs
			# no extra round trip. Empty for a user who can't open the app anyway.
			"resource_permissions": _resource_permissions() if allowed else {},
			# The bespoke (custom-UI) report routes this user may open — their backend Report
			# anchor grants a role they hold. The SPA route guard denies any other report route.
			"report_routes": _permitted_report_routes() if allowed else [],
			"reason": reason,
			"developer_mode": developer_mode,
		}
	)


def _permitted_report_routes():
	"""The custom report routes the current user may open (see buildsuite_core.report_access)."""
	from buildsuite_core.report_access import permitted_report_routes

	return permitted_report_routes()


# The DocPerm ptypes the SPA gates on, mapped to the short cap keys usePermissions reads
# (c=create, r=read, e=write/edit, d=delete, x=submit). Kept here so the payload speaks the
# frontend's vocabulary and the resolver stays a straight lookup.
_CAP_PTYPES = {"c": "create", "r": "read", "e": "write", "d": "delete", "x": "submit"}


def _resource_permissions() -> dict:
	"""The current user's effective caps for every mapped resource, derived from
	``frappe.has_permission`` — the single source of truth the SPA gates on.

	Each resource → ``{c, r, e, d, x, writeScope, deleteScope}``. ``writeScope`` /
	``deleteScope`` are ``"all" | "own" | "none"``: a persona whose write is granted only
	via an ``if_owner`` DocPerm reports ``"own"`` so the SPA can keep its own-record gating
	(edit/delete only your own drafts) that a bare boolean can't express.
	"""
	out = {}
	for key, doctype in RESOURCE_DOCTYPES.items():
		if not frappe.db.exists("DocType", doctype):
			# A Doctype absent on this site (e.g. an ERPNext module not installed) is simply
			# "no access" rather than an error — keeps the payload shape stable.
			out[key] = {c: False for c in _CAP_PTYPES}
			out[key].update({"writeScope": "none", "deleteScope": "none"})
			continue
		caps = {
			cap: bool(frappe.has_permission(doctype, ptype=ptype))
			for cap, ptype in _CAP_PTYPES.items()
		}
		caps["writeScope"] = _ptype_scope(doctype, "write") if caps["e"] else "none"
		caps["deleteScope"] = _ptype_scope(doctype, "delete") if caps["d"] else "none"
		out[key] = caps
	return out


def _ptype_scope(doctype: str, ptype: str) -> str:
	"""Whether the user's grant of ``ptype`` on ``doctype`` is unrestricted ("all") or
	limited to their own records ("own"). ``has_permission`` alone can't tell these apart —
	it's True for both — so we inspect the resolved role perms' ``if_owner`` map."""
	perms = frappe.permissions.get_role_permissions(doctype, user=frappe.session.user)
	if not perms.get(ptype):
		return "none"
	# if_owner may be absent or present-but-None; normalise before indexing.
	return "own" if (perms.get("if_owner") or {}).get(ptype) else "all"


@frappe.whitelist(methods=["GET"])
def get_resource_permissions():
	"""Standalone accessor for the derived resource caps (also embedded in
	``get_access_context``). UI gating only; server-side enforcement is unchanged."""
	if not _has_app_permission(log_denial=False):
		return {}
	return _resource_permissions()
