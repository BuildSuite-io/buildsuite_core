"""Record-level access for the Task Progress Entry doctype.

A progress entry inherits the team scoping of the project behind its `task`
(Task Progress Entry has no `project` field — it links to a Task). Procurement
Officer and Store Keeper have no DocPerm at all (hidden).

Own-scope for Site Engineer / Foreman:
  - edit (write): only their OWN-created entries (owner), any time
  - delete: only their OWN-created entries, and only within 24h of creation
Full-write roles (Director, PM, BS-Admin, System Manager) bypass the own-scope.
"""

import frappe
from frappe.utils import get_datetime, now_datetime

from buildsuite_core.permissions.project import _is_scoped, _is_project_member

FULL_WRITE_ROLES = {
    "BuildSuite Director",
    "BuildSuite PM",
    "BuildSuite Administrator",
    "System Manager",
}
OWN_SCOPE_ROLES = {"BuildSuite Site Engineer", "BuildSuite Foreman"}

_DELETE_WINDOW_HOURS = 24


def _entry_project(doc):
    task = getattr(doc, "task", None)
    if not task:
        return None
    return frappe.db.get_value("Task", task, "project")


def _within_delete_window(doc):
    if not getattr(doc, "creation", None):
        return True  # unsaved / brand-new — not blocked by the window
    age = now_datetime() - get_datetime(doc.creation)
    return age.total_seconds() <= _DELETE_WINDOW_HOURS * 3600


def get_task_progress_entry_permission_query(user):
    if not user:
        user = frappe.session.user
    if not _is_scoped(user):
        return ""

    return (
        "(`tabTask Progress Entry`.task IN ("
        "SELECT `name` FROM `tabTask` WHERE `project` IN ("
        "SELECT `parent` FROM `tabProject Team` "
        f"WHERE `user` = {frappe.db.escape(user)} AND `parenttype` = 'Project'"
        ")))"
    )


def has_task_progress_entry_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user
    if not _is_scoped(user):
        return True

    project = _entry_project(doc)
    if ptype == "create":
        return (not project) or _is_project_member(user, project)
    if not getattr(doc, "name", None):
        return True
    if project and not _is_project_member(user, project):
        return False

    roles = set(frappe.get_roles(user))
    if ptype == "write":
        if roles & FULL_WRITE_ROLES:
            return True
        return bool(roles & OWN_SCOPE_ROLES) and doc.owner == user
    if ptype == "delete":
        if roles & FULL_WRITE_ROLES:
            return True
        return bool(roles & OWN_SCOPE_ROLES) and doc.owner == user and _within_delete_window(doc)

    return True
