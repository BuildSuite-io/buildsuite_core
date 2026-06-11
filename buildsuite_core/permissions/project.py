"""Team-membership scoping for the Project doctype.

Base CRUD comes from role DocPerms (see buildsuite_core.permissions.setup). These
hooks only narrow the record set a user can see/touch based on Project Team
membership. has_permission is a Frappe DENY gate — returning True never grants
beyond DocPerm, it only declines to object.
"""

import frappe

# Never scoped — see every project. HR's read-only is enforced by DocPerm, not here.
EXEMPT_ROLES = {"BuildSuite Director", "BuildSuite HR Manager"}

# Unrestricted until the user joins any team; scoped to teamed projects thereafter.
FLIP_ROLES = {"BuildSuite PM", "System Manager", "BuildSuite Administrator"}

# Always scoped to projects the user is a team member of.
TEAM_ONLY_ROLES = {
    "BuildSuite Estimator",
    "BuildSuite QS",
    "BuildSuite Site Engineer",
    "BuildSuite Foreman",
    "BuildSuite Procurement Officer",
    "BuildSuite Store Keeper",
    "BuildSuite Accountant",
}


def _has_any_membership(user):
    return bool(frappe.db.exists("Project Team", {"user": user, "parenttype": "Project"}))


def _is_scoped(user):
    """Whether this user's project visibility should be restricted to team membership."""
    if user == "Administrator":
        return False

    roles = set(frappe.get_roles(user))
    if roles & EXEMPT_ROLES:
        return False
    if roles & FLIP_ROLES:
        return _has_any_membership(user)
    # TEAM_ONLY roles, and anyone without a BuildSuite role, are scoped.
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

    return bool(frappe.db.exists("Project Team", {
        "parent": doc.name,
        "parenttype": "Project",
        "user": user,
    }))
