"""Record-level access for the Stage Planning doctype.

Stage Planning inherits the parent Project's team scoping. CRUD own-scope:
  - Site Engineer / Foreman: edit/delete only their OWN-created stages, and only
    while the stage is still editable (Draft / Rejected — not after submit).
Full roles (Director, PM, BS-Admin, System Manager) have full CRUD within visible
projects. The Submit/Approve/Reject/Revise actions are governed by the Stage
Planning Approval workflow (see setup_stage_planning_workflow), not DocPerm.
"""

import frappe

from buildsuite_core.permissions.project import _is_scoped, _is_project_member

FULL_WRITE_ROLES = {
    "BuildSuite Director",
    "BuildSuite PM",
    "BuildSuite Administrator",
    "System Manager",
}
OWN_SCOPE_ROLES = {"BuildSuite Site Engineer", "BuildSuite Foreman"}

# Workflow states in which an own-scope creator may still edit/delete their stage.
_EDITABLE_STATES = {None, "", "Draft", "Rejected"}


def get_stage_planning_permission_query(user):
    if not user:
        user = frappe.session.user
    if not _is_scoped(user):
        return ""

    return (
        "(`tabStage Planning`.project IN ("
        "SELECT `parent` FROM `tabProject Team` "
        f"WHERE `user` = {frappe.db.escape(user)} AND `parenttype` = 'Project'"
        "))"
    )


def has_stage_planning_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user
    if not _is_scoped(user):
        return True

    project = getattr(doc, "project", None)
    if ptype == "create":
        return (not project) or _is_project_member(user, project)
    if not getattr(doc, "name", None):
        return True
    if project and not _is_project_member(user, project):
        return False

    if ptype in ("write", "delete"):
        roles = set(frappe.get_roles(user))
        if roles & FULL_WRITE_ROLES:
            return True
        if roles & OWN_SCOPE_ROLES and doc.owner == user:
            return doc.get("workflow_state") in _EDITABLE_STATES
        return False

    return True
