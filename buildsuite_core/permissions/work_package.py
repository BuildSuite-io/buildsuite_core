"""Record-level access for the Work Package doctype.

Work Package visibility inherits the parent Project's team scoping (same EXEMPT /
FLIP / TEAM-ONLY buckets). All non-full roles are read-only at the DocPerm level,
so no own-scope rules are needed — visibility is the only thing to enforce.
"""

import frappe

from buildsuite_core.permissions.project import _is_project_member, _is_scoped


def get_work_package_permission_query(user):
	if not user:
		user = frappe.session.user
	if not _is_scoped(user):
		return ""

	return (
		"(`tabWork Package`.project IN ("
		"SELECT `parent` FROM `tabProject Team` "
		f"WHERE `user` = {frappe.db.escape(user)} AND `parenttype` = 'Project'"
		"))"
	)


def has_work_package_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if not _is_scoped(user):
		return True

	project = getattr(doc, "project", None)
	if ptype == "create":
		return (not project) or _is_project_member(user, project)
	if not getattr(doc, "name", None):
		return True
	return _is_project_member(user, project)
