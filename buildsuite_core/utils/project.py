import frappe
from frappe import _


# BuildSuite project_status -> native ERPNext Project status (Open/Completed/Cancelled).
# New/Ongoing/Delayed all map to the active "Open"; only Completed closes the project.
_PROJECT_STATUS_TO_NATIVE = {
    "New": "Open",
    "Ongoing": "Open",
    "Delayed": "Open",
    "Completed": "Completed",
}


def sync_project_status(doc, method=None):
    """Keep native `status` aligned with the BuildSuite `project_status` enum.

    project_status (New/Ongoing/Delayed/Completed) is the source of truth shown in
    the UI; the native status only carries Open/Completed/Cancelled, so we map onto
    it. Defaults a blank project_status to New.
    """
    if not getattr(doc, "project_status", None):
        doc.project_status = "New"
    doc.status = _PROJECT_STATUS_TO_NATIVE.get(doc.project_status, "Open")


def set_company_on_insert(doc, method=None):
    """Default/inherit company before insert (PRJ-005, PRJ-012).

    Subprojects inherit the parent's company; top-level projects fall back to the
    user's default company when none was chosen (covers single-company sites where
    the field is hidden in the UI).
    """
    if doc.get("parent_project"):
        parent_company = frappe.db.get_value("Project", doc.parent_project, "company")
        if parent_company:
            doc.company = parent_company
            return

    if not doc.get("company"):
        # Inferred from the creating user's company (the Vue form no longer asks
        # for it), falling back to the site default.
        doc.company = (
            frappe.db.get_value("User", frappe.session.user, "company")
            or frappe.defaults.get_user_default("Company")
            or frappe.db.get_single_value("Global Defaults", "default_company")
        )


def enforce_company_rules(doc, method=None):
    """Lock company after create and keep subproject company inherited (PRJ-005, PRJ-013)."""
    # Subprojects always track their parent's company.
    if doc.get("parent_project"):
        parent_company = frappe.db.get_value("Project", doc.parent_project, "company")
        if parent_company:
            doc.company = parent_company

    # Company is read-only after create: revert any attempt to change it on edit.
    if not doc.is_new():
        before = doc.get_doc_before_save()
        if before and before.company and doc.company != before.company:
            doc.company = before.company


# Accounting / stock DocTypes that, if they reference a project, must block its
# deletion. Each entry: (doctype, fieldname holding the project link).
_FINANCIAL_LINKS = [
    ("GL Entry", "project"),
    ("Journal Entry Account", "project"),
    ("Sales Invoice", "project"),
    ("Purchase Invoice", "project"),
    ("Stock Entry", "project"),
    ("Payment Entry", "project"),
]


def _projects_in_tree(project):
    """All project names in the subtree rooted at `project` (inclusive)."""
    names = [project]
    children = frappe.get_all("Project", filters={"parent_project": project}, pluck="name")
    for child in children:
        names.extend(_projects_in_tree(child))
    return names


def _assert_no_financial_links(project_names):
    for doctype, field in _FINANCIAL_LINKS:
        if not frappe.db.exists("DocType", doctype):
            continue
        # Only consider field if it exists on the doctype.
        meta = frappe.get_meta(doctype)
        if not meta.has_field(field):
            continue
        if frappe.db.exists(doctype, {field: ("in", project_names)}):
            frappe.throw(
                _("Cannot delete: {0} records are linked to this project (or a subproject). "
                  "Remove the accounting/stock entries first.").format(doctype)
            )


def cascade_delete_project(doc, method=None):
    """Guarded cascade delete (PRJ-014, STG-011).

    Blocks if any accounting/stock entry references the project or its subprojects;
    otherwise removes subprojects, work packages, tasks, TPEs, stages, and
    attachments. Task deletion fires its own cascade (TPEs/attachments).
    """
    project_names = _projects_in_tree(doc.name)
    _assert_no_financial_links(project_names)

    # Suppress progress rollup while we tear the tree down (tasks deleting here
    # would otherwise recompute ancestors that are about to be deleted too).
    previous = frappe.flags.get("buildsuite_cascading")
    frappe.flags.buildsuite_cascading = True
    try:
        # Delete descendants depth-first: child projects first (each re-enters this hook).
        for child in frappe.get_all("Project", filters={"parent_project": doc.name}, pluck="name"):
            frappe.delete_doc("Project", child, ignore_permissions=True, force=True)

        # Stage Plannings for this project.
        for stage in frappe.get_all("Stage Planning", filters={"project": doc.name}, pluck="name"):
            frappe.delete_doc("Stage Planning", stage, ignore_permissions=True, force=True)

        # Tasks (their on_trash cascades TPEs + attachments).
        for task in frappe.get_all("Task", filters={"project": doc.name}, pluck="name"):
            frappe.delete_doc("Task", task, ignore_permissions=True, force=True)

        # Work Packages.
        for wp in frappe.get_all("Work Package", filters={"project": doc.name}, pluck="name"):
            frappe.delete_doc("Work Package", wp, ignore_permissions=True, force=True)
    finally:
        frappe.flags.buildsuite_cascading = previous

    # Attachments on this project.
    _delete_attachments("Project", doc.name)


def _delete_attachments(doctype, name):
    for f in frappe.get_all(
        "File", filters={"attached_to_doctype": doctype, "attached_to_name": name}, pluck="name"
    ):
        frappe.delete_doc("File", f, ignore_permissions=True, force=True)


def backfill_project_status(doc=None, method=None):
    """Populate project_status on Projects where it's empty (idempotent).

    Derives from native status: Completed -> Completed, else New. Wired into
    after_migrate so existing projects render a badge.
    """
    rows = frappe.get_all("Project", fields=["name", "status", "project_status"])
    updated = 0
    for row in rows:
        if row.project_status:
            continue
        new_status = "Completed" if row.status == "Completed" else "New"
        frappe.db.set_value("Project", row.name, "project_status", new_status, update_modified=False)
        updated += 1
    if updated:
        frappe.db.commit()
    return updated


def seed_from_template_on_insert(doc, method=None):
    if not doc.project_type:
        return
    if not (doc.custom_seed_default_stages or doc.custom_seed_default_tasks):
        return

    template_name = frappe.db.get_value(
        'BuildSuite Project Template',
        {'project_type': doc.project_type},
        'name'
    )
    if not template_name:
        return

    template = frappe.get_doc('BuildSuite Project Template', template_name)

    from buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.buildsuite_project_template import (
        create_stage_plan,
        create_task,
    )

    seed_stages = bool(doc.custom_seed_default_stages)
    seed_tasks = bool(doc.custom_seed_default_tasks)

    # Three seed modes:
    #   Stages + Tasks -> stages created WITH their nested tasks, plus project-level tasks.
    #   Stages only    -> empty stages (no tasks created at all).
    #   Tasks only     -> no stages; every template task (project-level AND the ones
    #                     nested in stage plans) created as a plain project task.
    if seed_stages:
        for row in template.stage_plans:
            try:
                stage_plan_doc = frappe.get_doc('Stage Plan Template', row.stage_plan)
                create_stage_plan(doc.name, stage_plan_doc, with_tasks=seed_tasks)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f'BuildSuite: seed stage plan "{row.stage_plan}" for project "{doc.name}"'
                )

    if seed_tasks:
        for row in template.project_task:
            try:
                create_task(doc.name, row)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f'BuildSuite: seed task "{row.task}" for project "{doc.name}"'
                )
        # Tasks-only: the tasks that would otherwise be nested under stage plans
        # are still wanted — create them as project-level tasks (no stage).
        if not seed_stages:
            for row in template.stage_plans:
                try:
                    stage_plan_doc = frappe.get_doc('Stage Plan Template', row.stage_plan)
                    for task_row in stage_plan_doc.tasks:
                        create_task(doc.name, task_row)
                except Exception:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f'BuildSuite: seed nested tasks from stage plan "{row.stage_plan}" for project "{doc.name}"'
                    )


@frappe.whitelist()
def get_project_template_summary(project_type):
    """Preview summary of the template for a Project Type (used by the create form).

    Returns the stage names and the TOTAL task count — the flat project-level
    `project_task` rows PLUS every task nested inside the template's stage plans.
    The task count is what the "Import default tasks" option will seed.
    """
    if not project_type:
        return {'exists': False}

    template_name = frappe.db.get_value(
        'BuildSuite Project Template', {'project_type': project_type}, 'name'
    )
    if not template_name:
        return {'exists': False}

    template = frappe.get_doc('BuildSuite Project Template', template_name)

    stage_names = []
    nested_task_count = 0
    for row in template.stage_plans:
        stage_plan_doc = frappe.get_doc('Stage Plan Template', row.stage_plan)
        stage_names.append(stage_plan_doc.stage_name)
        nested_task_count += len(stage_plan_doc.tasks or [])

    return {
        'exists': True,
        'stage_names': stage_names,
        'stage_count': len(stage_names),
        'task_count': len(template.project_task or []) + nested_task_count,
    }


@frappe.whitelist()
def seed_stages_from_template(project):
    """PTT-005 — append stages from the matching BuildSuite Project Template onto
    an EXISTING project. Mirrors the create-time seed (seed_from_template_on_insert)
    and reuses create_stage_plan, so each seeded stage carries its template tasks
    at 100% planned qty. Returns the number of stages created.
    """
    doc = frappe.get_doc('Project', project)
    doc.check_permission('write')

    if not doc.project_type:
        frappe.throw(_("This project has no Project Type, so there is no template to seed from."))

    template_name = frappe.db.get_value(
        'BuildSuite Project Template', {'project_type': doc.project_type}, 'name'
    )
    if not template_name:
        frappe.throw(_("No template is configured for project type {0}.").format(doc.project_type))

    template = frappe.get_doc('BuildSuite Project Template', template_name)
    from buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.buildsuite_project_template import (
        create_stage_plan,
    )

    count = 0
    for row in template.stage_plans:
        stage_plan_doc = frappe.get_doc('Stage Plan Template', row.stage_plan)
        create_stage_plan(doc.name, stage_plan_doc, with_tasks=True)
        count += 1
    return {'seeded': count}


def ensure_project_team_membership(doc, method=None):
    """PRM-002 — project visibility is team-membership based. Ensure the project's
    creator and its assigned project_manager are team members, so the project is
    visible to them under the team-scoped permission model. Idempotent; inserts the
    child rows directly to avoid re-triggering the parent's on_update.
    """
    _ensure_team_member(doc.name, doc.owner)
    _ensure_team_member(doc.name, getattr(doc, 'project_manager', None))


def _ensure_team_member(project_name, user):
    if not user or user == 'Administrator':
        return
    if not frappe.db.exists('User', user):
        return
    if frappe.db.exists('Project Team', {
        'parenttype': 'Project',
        'parentfield': 'custom_team_members',
        'parent': project_name,
        'user': user,
    }):
        return
    frappe.get_doc({
        'doctype': 'Project Team',
        'parenttype': 'Project',
        'parentfield': 'custom_team_members',
        'parent': project_name,
        'user': user,
        'full_name': frappe.db.get_value('User', user, 'full_name'),
    }).insert(ignore_permissions=True)


@frappe.whitelist()
def create_warehouse_for_project(doc, method=None):
    # Create Projects Group Warehouse
    if not frappe.db.exists(
        "Warehouse",
        {"warehouse_name": "Projects", "company": doc.company}
    ):
        warehouse = frappe.new_doc("Warehouse")
        warehouse.warehouse_name = "Projects"
        warehouse.company = doc.company
        warehouse.is_group = 1
        warehouse.insert(ignore_permissions=True)

    parent_warehouse = frappe.db.get_value(
        "Warehouse",
        {"warehouse_name": "Projects", "company": doc.company},
        "name"
    )

    # Create Project Group Warehouse
    if not frappe.db.exists(
        "Warehouse",
        {"warehouse_name": doc.project_name, "company": doc.company}
    ):
        warehouse = frappe.new_doc("Warehouse")
        warehouse.warehouse_name = doc.project_name
        warehouse.parent_warehouse = parent_warehouse
        warehouse.company = doc.company
        warehouse.is_group = 1
        warehouse.insert(ignore_permissions=True)

    project_parent_warehouse = frappe.db.get_value(
        "Warehouse",
        {"warehouse_name": doc.project_name, "company": doc.company},
        "name"
    )

    # Create Store Warehouse
    project_warehouse = f"{doc.project_name} Store"

    if not frappe.db.exists(
        "Warehouse",
        {"warehouse_name": project_warehouse, "company": doc.company}
    ):
        stock_account = frappe.db.get_value(
            "Account",
            {
                "account_type": "Stock",
                "company": doc.company,
                "is_group": 0
            },
            "name"
        )

        warehouse = frappe.new_doc("Warehouse")
        warehouse.warehouse_name = project_warehouse
        warehouse.project = doc.name
        warehouse.parent_warehouse = project_parent_warehouse
        warehouse.account = stock_account
        warehouse.company = doc.company
        warehouse.insert(ignore_permissions=True)


@frappe.whitelist()
def delete_warehouse_for_project(doc, method=None):
    project_warehouse = f"{doc.project_name} Store"

    warehouse_name = frappe.db.get_value(
        "Warehouse",
        {
            "warehouse_name": project_warehouse,
            "company": doc.company
        },
        "name"
    )

    if warehouse_name:
        frappe.delete_doc(
            "Warehouse",
            warehouse_name,
            ignore_permissions=True
        )
