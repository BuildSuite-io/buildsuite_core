# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Admin actions for the BuildSuite default role-permission matrix.

Historically the shipped defaults were re-applied on every app update (one-time resync
patches + the additive read-mirror on after_migrate), which silently overwrote any DocPerm
a client had tuned in Desk. Now that the SPA derives its gating entirely from backend
DocPerms, an update must NOT reset a client's customized permissions. These two whitelisted
actions replace the auto-reset:

- ``restore_default_role_permissions()`` — re-apply the shipped default matrix on demand
  (the old auto-reset, now an explicit, confirmed admin action).
- ``export_role_permissions()`` — dump the site's CURRENT BuildSuite-role DocPerms as JSON so
  a client's customizations can be handed back and folded into the shipped defaults.
"""

import frappe
from frappe import _

from buildsuite_core.permissions.setup import BUILDSUITE_ROLES

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}

# Permission flags stored per (doctype, role) Custom DocPerm row — exported in this order so a
# diff against permissions/setup.py's *_ROLE_PERMS matrices reads cleanly.
_PERM_FIELDS = (
	"permlevel",
	"if_owner",
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"print",
	"email",
	"share",
)


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(
			_("Only an administrator can manage role permissions."), frappe.PermissionError
		)


@frappe.whitelist()
def restore_default_role_permissions():
	"""Re-apply BuildSuite's shipped default DocPerm matrix for every managed doctype/role.

	This OVERWRITES any in-Desk permission customizations back to the defaults — the perm slice of
	the routine that used to run on app update, now an explicit, confirmed admin action. Idempotent.

	Re-applying the matrix (chiefly the child-table read mirror) is minutes-long, so it runs as a
	background job rather than blocking the request; the caller sees the change once the job lands.
	"""
	_require_admin()
	frappe.enqueue(
		"buildsuite_core.permissions.setup.restore_role_permissions",
		queue="long",
		timeout=1800,
		job_name="buildsuite-restore-role-permissions",
	)
	return {"ok": True, "queued": True, "roles": list(BUILDSUITE_ROLES)}


@frappe.whitelist()
def export_role_permissions():
	"""The site's CURRENT DocPerms for the BuildSuite roles, grouped by doctype.

	A snapshot the client hands back so the shipped defaults can be aligned to their edits.
	Only BuildSuite roles are included (System Manager's blanket grant is noise for alignment).
	"""
	_require_admin()
	roles = list(BUILDSUITE_ROLES)
	rows = frappe.get_all(
		"Custom DocPerm",
		filters={"role": ["in", roles]},
		fields=["parent", "role", *(_PERM_FIELDS)],
		order_by="parent asc, role asc, permlevel asc",
	)
	by_doctype = {}
	for r in rows:
		by_doctype.setdefault(r.parent, []).append(
			{"role": r.role, **{f: int(r.get(f) or 0) for f in _PERM_FIELDS}}
		)
	return {
		"site": frappe.local.site,
		"roles": roles,
		"doctypes": sorted(by_doctype),
		"permissions": by_doctype,
	}
