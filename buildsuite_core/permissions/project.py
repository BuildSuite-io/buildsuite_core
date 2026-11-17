"""Team-membership scoping for the Project doctype.

Base CRUD comes from role DocPerms (see buildsuite_core.permissions.setup). These
hooks only narrow the record set a user can see/touch based on Project Team
membership. has_permission is a Frappe DENY gate — returning True never grants
beyond DocPerm, it only declines to object.
"""

import frappe

# Persona.project_visibility — how much of the project tree a persona's users see. Set per persona
# (Settings > Personas, or the Persona form in the desk), so a site can scope a persona differently
# without a code change.
ALL_PROJECTS = "All projects"  # every project their role permissions allow
UNTIL_TEAMED = "All projects until added to a team"  # then only the projects whose team they're on
TEAM_ONLY = "Team projects only"  # only the projects whose team they're on

# System Manager is the platform administrator: never scoped, whatever their persona says.
ALWAYS_ALL_ROLES = {"System Manager"}

# --------------------------------------------------------------------------------------------- #
# The role-based rule this replaced. Still used, but only for a user who has NO persona (one who
# predates personas, or was given BuildSuite roles by hand) and to seed each existing custom
# persona's setting from its roles when the field arrived (patches/set_persona_project_visibility).
# --------------------------------------------------------------------------------------------- #
EXEMPT_ROLES = {
	"BuildSuite Director",
	"System Manager",
	"BuildSuite Administrator",
}
FLIP_ROLES = {
	"BuildSuite PM",
	"BuildSuite HR Manager",
	"BuildSuite Estimator",
	"BuildSuite QS",
	"BuildSuite Procurement Officer",
	"BuildSuite Store Keeper",
	"BuildSuite Accountant",
}

TEAM_ONLY_ROLES = {
	"BuildSuite Site Engineer",
	"BuildSuite Foreman",
}


def visibility_from_roles(roles):
	"""The project visibility the role-based rule gives a set of roles: the widest any role allows.
	Anyone without a BuildSuite role was team-scoped."""
	roles = set(roles)
	if roles & EXEMPT_ROLES:
		return ALL_PROJECTS
	if roles & FLIP_ROLES:
		return UNTIL_TEAMED
	return TEAM_ONLY


def project_visibility(user):
	"""How much of the project tree this user sees: their persona's setting, else (no persona) the
	role-based rule. Administrator and System Manager always see everything."""
	if user == "Administrator":
		return ALL_PROJECTS
	roles = set(frappe.get_roles(user))
	if roles & ALWAYS_ALL_ROLES:
		return ALL_PROJECTS
	persona = frappe.get_cached_value("User", user, "persona")
	if persona:
		visibility = frappe.get_cached_value("Persona", persona, "project_visibility")
		if visibility:
			return visibility
	return visibility_from_roles(roles)


def _has_any_membership(user):
	return bool(frappe.db.exists("Project Team", {"user": user, "parenttype": "Project"}))


def _is_project_member(user, project):
	"""Shared by Task / Work Package / Task Progress Entry / Stage Planning scoping."""
	if not project:
		return False
	return bool(
		frappe.db.exists(
			"Project Team",
			{
				"parent": project,
				"parenttype": "Project",
				"user": user,
			},
		)
	)


def _is_scoped(user):
	"""Whether this user's project visibility should be restricted to team membership."""
	visibility = project_visibility(user)
	if visibility == ALL_PROJECTS:
		return False
	if visibility == UNTIL_TEAMED:
		return _has_any_membership(user)
	# Team projects only — and any value this code does not know, the safe side.
	return True


def get_project_permission_query(user):
	if not user:
		user = frappe.session.user
	if not _is_scoped(user):
		return ""

	return (
		"(`tabProject`.name IN ("
		"SELECT `parent` FROM `tabProject Team` "
		f"WHERE `user` = {frappe.db.escape(user)} AND `parenttype` = 'Project'"
		"))"
	)


def has_project_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if not _is_scoped(user):
		return True

	# Creating a new project isn't gated by team membership (the project doesn't
	# exist yet) — let the role DocPerm decide.
	if ptype == "create" or not getattr(doc, "name", None):
		return True

	return bool(
		frappe.db.exists(
			"Project Team",
			{
				"parent": doc.name,
				"parenttype": "Project",
				"user": user,
			},
		)
	)
