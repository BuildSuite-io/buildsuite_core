"""Seed BuildSuite roles and Project DocPerms.

Run idempotently from install.after_migrate / after_install. The CRUD matrix here
is the single source of truth for the per-persona base permissions on Project;
team-membership scoping is layered on top in buildsuite_core.permissions.project.
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

# All BuildSuite roles, for the app-level access gate (api.permission).
BUILDSUITE_ROLES = tuple(PROJECT_ROLE_PERMS.keys())

# Every flag we may set on a DocPerm — anything not granted is explicitly cleared.
_PTYPES = ("read", "write", "create", "delete", "report", "export", "print")


def _ensure_role(role_name):
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,
        }).insert(ignore_permissions=True)


def setup_project_permissions():
    from frappe.permissions import add_permission, update_permission_property

    for role, perms in PROJECT_ROLE_PERMS.items():
        _ensure_role(role)
        add_permission("Project", role, 0)
        for ptype in _PTYPES:
            update_permission_property(
                "Project", role, 0, ptype, perms.get(ptype, 0),
                validate=False,
            )
