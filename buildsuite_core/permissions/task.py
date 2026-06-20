"""Record-level access for the Task doctype.

Task visibility *inherits* the parent Project's team scoping — a task is visible
only when the user can see its project (same EXEMPT / FLIP / TEAM-ONLY buckets as
buildsuite_core.permissions.project). On top of that, two roles get an own-scope
restriction on edit/delete (enforced here because a has_permission hook can only
DENY, never widen, a role DocPerm):

  - Site Engineer  -> edit/delete only tasks they CREATED (owner)
  - Foreman        -> edit/delete only tasks they created OR are ASSIGNED to

Creator = Frappe's built-in `owner`. Assignee = Frappe-native assignment (`_assign`).
"""

import frappe

from buildsuite_core.permissions.project import _is_project_member, _is_scoped

# Roles with unrestricted write/create/delete within their visible projects —
# no own-scope restriction applies to them.
FULL_TASK_WRITE_ROLES = {
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Administrator",
	"System Manager",
}


def _is_assignee(doc, user):
	assigned = doc.get("_assign")
	if not assigned:
		return False
	try:
		return user in frappe.parse_json(assigned)
	except Exception:
		return False


def _can_modify_task(doc, user):
	roles = set(frappe.get_roles(user))
	if roles & FULL_TASK_WRITE_ROLES:
		return True
	if "BuildSuite Site Engineer" in roles and doc.owner == user:
		return True
	if "BuildSuite Foreman" in roles and (doc.owner == user or _is_assignee(doc, user)):
		return True
	return False


def get_task_permission_query(user):
	if not user:
		user = frappe.session.user
	if not _is_scoped(user):
		return ""

	# A task is visible when its parent project is one the user is teamed on.
	return (
		"(`tabTask`.project IN ("
		"SELECT `parent` FROM `tabProject Team` "
		f"WHERE `user` = {frappe.db.escape(user)} AND `parenttype` = 'Project'"
		"))"
	)


def has_task_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if not _is_scoped(user):
		return True

	project = getattr(doc, "project", None)

	# Creating a task is allowed within a visible project (or before one is set).
	if ptype == "create":
		return (not project) or _is_project_member(user, project)

	if not getattr(doc, "name", None):
		return True

	# Must be able to see the task's project at all.
	if project and not _is_project_member(user, project):
		return False

	# Read / report / print / export need only project visibility; write & delete
	# additionally honour the Site Engineer / Foreman own-scope rules.
	if ptype in ("write", "delete"):
		return _can_modify_task(doc, user)

	return True
