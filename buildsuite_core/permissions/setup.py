"""Seed BuildSuite roles and Project/Task DocPerms.

Run idempotently from install.after_migrate / after_install. The CRUD matrices
here are the single source of truth for the per-persona base permissions; the
team-membership scoping (and Task own-scope rules) are layered on top in
buildsuite_core.permissions.project and buildsuite_core.permissions.task.
"""

import frappe

# Per-role base permissions on Project at permlevel 0 (from the persona spec).
# System Manager is intentionally absent — it keeps its native full Project perms.
PROJECT_ROLE_PERMS = {
    "BuildSuite Director":            {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite PM":                  {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Administrator":       {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Estimator":           {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite QS":                  {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Procurement Officer": {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Accountant":          {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite HR Manager":          {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Site Engineer":       {"read": 1, "report": 1, "print": 1},
    "BuildSuite Store Keeper":        {"read": 1, "report": 1, "print": 1},
    "BuildSuite Foreman":             {"read": 1, "print": 1},
}

# Per-role base permissions on Task at permlevel 0 (from the Task persona spec).
# Site Engineer / Foreman get write+create+delete at the DocPerm level; the
# own-scope restriction (edit/delete only own-created or assigned tasks) is
# enforced in buildsuite_core.permissions.task.has_task_permission, since a
# has_permission hook can only DENY, never widen, a DocPerm grant.
TASK_ROLE_PERMS = {
    "BuildSuite Director":            {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite PM":                  {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Administrator":       {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Estimator":           {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite QS":                  {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite Site Engineer":       {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "print": 1},
    "BuildSuite Foreman":             {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1},
    "BuildSuite Procurement Officer": {"read": 1, "report": 1, "print": 1},
    "BuildSuite Store Keeper":        {"read": 1, "report": 1, "print": 1},
    "BuildSuite Accountant":          {"read": 1, "report": 1, "export": 1, "print": 1},
    "BuildSuite HR Manager":          {"read": 1, "report": 1, "print": 1},
}

# All BuildSuite roles, for the app-level access gate (api.permission).
BUILDSUITE_ROLES = tuple(PROJECT_ROLE_PERMS.keys())

# User.persona Select value -> the role that persona grants. The persona option
# strings mirror the `name` fields in frontend/src/data/roles.js so the frontend
# and backend agree on one vocabulary. "System Manager (Admin)" maps to Frappe's
# native System Manager role (not a BuildSuite role).
PERSONA_TO_ROLE = {
    "Director / Owner":         "BuildSuite Director",
    "Project Manager":          "BuildSuite PM",
    "Estimator":                "BuildSuite Estimator",
    "Quantity Surveyor":        "BuildSuite QS",
    "Site Engineer":            "BuildSuite Site Engineer",
    "Foreman / Supervisor":     "BuildSuite Foreman",
    "Procurement Officer":      "BuildSuite Procurement Officer",
    "Store Keeper":             "BuildSuite Store Keeper",
    "Accountant":               "BuildSuite Accountant",
    "HR Manager":               "BuildSuite HR Manager",
    "System Manager (Admin)":   "System Manager",
    "BuildSuite Administrator": "BuildSuite Administrator",
}

# Every flag we may set on a DocPerm — anything not granted is explicitly cleared.
_PTYPES = ("read", "write", "create", "delete", "report", "export", "print")


def _ensure_role(role_name):
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,
        }).insert(ignore_permissions=True)


def _apply_role_perms(doctype, role_perms):
    from frappe.permissions import add_permission, update_permission_property

    for role, perms in role_perms.items():
        _ensure_role(role)
        add_permission(doctype, role, 0)
        for ptype in _PTYPES:
            update_permission_property(
                doctype, role, 0, ptype, perms.get(ptype, 0),
                validate=False,
            )


def setup_project_permissions():
    _apply_role_perms("Project", PROJECT_ROLE_PERMS)


def setup_task_permissions():
    _apply_role_perms("Task", TASK_ROLE_PERMS)


def setup_record_permissions():
    """Seed roles + DocPerms for every BuildSuite-scoped doctype."""
    setup_project_permissions()
    setup_task_permissions()
