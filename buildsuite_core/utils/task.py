import frappe
from frappe.utils import flt
import json

def _wp_progress_from_tasks(tasks):
    if not tasks:
        return 0
    avg = sum(flt(t.get("progress", 0)) for t in tasks) / len(tasks)
    return min(round(avg), 100)


def _derive_wp_status(current, tasks):
    """Auto-advance Work Package status from its tasks' progress, while leaving
    manual states intact:
      - 'On Hold' is a manual pause — never auto-changed.
      - all tasks at 100%  -> 'Completed'.
      - any task in progress, while still 'Planned'/blank -> 'In Progress'.
      - otherwise unchanged (manual 'In Progress'/'Completed' is respected).
    Manual edits via the WP form still set any value; this only nudges forward.
    """
    if current == "On Hold":
        return current
    if tasks and all(flt(t.get("progress", 0)) >= 100 for t in tasks):
        return "Completed"
    if any(flt(t.get("progress", 0)) > 0 for t in tasks):
        if current in (None, "", "Planned"):
            return "In Progress"
    return current


def _sync_work_package(wp, tasks):
    progress = _wp_progress_from_tasks(tasks)
    current = frappe.db.get_value("Work Package", wp, "status")
    values = {"progress": progress}
    new_status = _derive_wp_status(current, tasks)
    if new_status != current:
        values["status"] = new_status
    frappe.db.set_value("Work Package", wp, values)


def update_work_package_progress(doc, method=None):
    if not doc.work_package:
        return

    tasks = frappe.get_all(
        "Task",
        filters={"work_package": doc.work_package},
        fields=["progress"],
    )
    _sync_work_package(doc.work_package, tasks)


def recalculate_work_package_on_task_trash(doc, method=None):
    """on_trash fires before the row is removed, so exclude the deleted task explicitly."""
    if not doc.work_package:
        return

    tasks = frappe.get_all(
        "Task",
        filters={"work_package": doc.work_package, "name": ("!=", doc.name)},
        fields=["progress"],
    )
    _sync_work_package(doc.work_package, tasks)

def sync_stage_tasks_on_update(doc, method=None):
    """
    Triggered whenever an ERPNext Task is saved/updated.
    Updates matching Child Table rows in Stage Planning.
    """
    # 1. Find all parent Stage Planning documents that reference this task
    # 'stage_planning_tasks' is the child table fieldname, 'task' is the link field
    parents = frappe.get_all(
        "Stage Planning Task",
        filters={"task": doc.name},
        fields=["parent"]
    )

    if not parents:
        return

    # Extract unique parent IDs
    parent_ids = set([p.parent for p in parents])

    for parent_id in parent_ids:
        # Load the full parent document wrapper
        parent_doc = frappe.get_doc("Stage Planning", parent_id)
        modified = False

        # 2. Iterate through child table rows and update matching references
        for child_row in parent_doc.stage_planning_tasks:
            if child_row.task == doc.name:
                # Update fields if they have changed
                if child_row.planned_start != doc.exp_start_date or child_row.planned_end != doc.exp_end_date:
                    child_row.planned_start = doc.exp_start_date
                    child_row.planned_end = doc.exp_end_date
                    modified = True

        # 3. Save the parent document if modifications occurred
        if modified:
            # flags.ignore_validate_update_after_submit bypasses restrictions if parent is submitted
            parent_doc.flags.ignore_validate_update_after_submit = True
            parent_doc.save(ignore_permissions=True)


def cascade_delete_task(doc, method=None):
    """Cascade delete a Task's children (TSK-013).

    Removes Task Progress Entries and file attachments tied to the task. The
    embedded task_progress_details child rows are removed with the task itself.
    TPE on_trash recomputes progress, but since the task is being deleted that's a
    harmless no-op.
    """
    # Signal so TPE on_trash skips the (now pointless) parent-task progress recompute.
    frappe.flags.buildsuite_deleting_task = doc.name
    try:
        for tpe in frappe.get_all("Task Progress Entry", filters={"task": doc.name}, pluck="name"):
            frappe.delete_doc("Task Progress Entry", tpe, ignore_permissions=True, force=True)
    finally:
        frappe.flags.buildsuite_deleting_task = None

    for f in frappe.get_all(
        "File", filters={"attached_to_doctype": "Task", "attached_to_name": doc.name}, pluck="name"
    ):
        frappe.delete_doc("File", f, ignore_permissions=True, force=True)


def sync_stage_tasks_on_delete(doc, method=None):
    """
    Triggered right before an ERPNext Task is deleted.
    Removes or clears matching Child Table rows in Stage Planning.
    """
    parents = frappe.get_all(
        "Stage Planning Task",
        filters={"task": doc.name},
        fields=["parent"]
    )

    if not parents:
        return

    parent_ids = set([p.parent for p in parents])

    for parent_id in parent_ids:
        parent_doc = frappe.get_doc("Stage Planning", parent_id)

        # Filter out the deleted task from the child table array
        original_count = len(parent_doc.stage_planning_tasks)
        parent_doc.stage_planning_tasks = [
            row for row in parent_doc.stage_planning_tasks if row.task != doc.name
        ]

        # Save if a row was dropped
        if len(parent_doc.stage_planning_tasks) < original_count:
            parent_doc.flags.ignore_validate_update_after_submit = True
            parent_doc.save(ignore_permissions=True)


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		task = frappe.get_doc("Task", name)
		task.task_status = status
		task.save()
from frappe.utils import getdate, today


def update_task_status(doc, method=None):
    current_date = getdate(today())
    old_doc = doc.get_doc_before_save()

    if (
        old_doc
        and old_doc.exp_end_date != doc.exp_end_date
        and doc.exp_end_date
        and getdate(doc.exp_end_date) >= current_date
        and doc.task_status == "In Delay"
    ):
        doc.task_status = "In Progress"

    # Set task status to In Delay automatically
    # if doc.task_status != "Completed":
    #     if doc.exp_end_date and getdate(doc.exp_end_date) < current_date:
    #         doc.task_status = "In Delay"

    #     elif (
    #         doc.exp_start_date
    #         and getdate(doc.exp_start_date) < current_date
    #         and doc.task_status not in ["Completed", "In Progress"]
    #     ):
    #         doc.task_status = "In Delay"

    # Sync ERPNext status field
    if doc.progress == 100:
        doc.status = "Completed"
        doc.task_status = "Completed"

    elif doc.task_status == "In Progress":
        doc.status = "Working"

    elif doc.task_status == "In Delay":
        doc.status = "Overdue"

    elif doc.task_status == "Yet To Start":
        doc.status = "Open"

    else:
        doc.status = "Open"

def update_task_status_insert(doc, method=None):
    current_date = getdate(today())

    # Set task status to In Delay automatically. Blocked is an explicit manual
    # status — never auto-flip it to In Delay.
    if doc.task_status not in ["Completed", "Blocked"]:
        if doc.exp_end_date and getdate(doc.exp_end_date) < current_date:
            doc.task_status = "In Delay"

        elif (
            doc.exp_start_date
            and getdate(doc.exp_start_date) < current_date
            and doc.task_status not in ["Completed", "In Progress"]
        ):
            doc.task_status = "In Delay"

    # Sync ERPNext status field
    if doc.progress == 100:
        doc.status = "Completed"
        doc.task_status = "Completed"

    elif doc.task_status == "In Progress":
        doc.status = "Working"

    elif doc.task_status == "In Delay":
        doc.status = "Overdue"

    elif doc.task_status == "Yet To Start":
        doc.status = "Open"

    else:
        doc.status = "Open"

from frappe.utils import flt


def _subtree_task_count(project):
    """Total tasks in a project's whole subtree (itself + all descendants).

    This is the weight a subproject contributes to its parent's progress rollup.
    """
    count = frappe.db.count("Task", {"project": project})
    for sub in frappe.get_all("Project", filters={"parent_project": project}, pluck="name"):
        count += _subtree_task_count(sub)
    return count


def _recompute_project_progress(project):
    """Weighted progress for one project = its direct tasks (weight 1 each) blended
    with each subproject's stored progress weighted by that subproject's task count.

    Written via db.set_value with percent_complete_method=Manual so erpnext's own
    auto-calc (which short-circuits on Manual) doesn't override the rollup.
    """
    direct = frappe.get_all("Task", filters={"project": project}, fields=["progress"])
    weighted = sum(flt(t.progress) for t in direct)
    weight = len(direct)

    for sub in frappe.get_all(
        "Project", filters={"parent_project": project}, fields=["name", "percent_complete"]
    ):
        sub_weight = _subtree_task_count(sub.name)
        if sub_weight:
            weighted += flt(sub.percent_complete) * sub_weight
            weight += sub_weight

    percent_complete = round(weighted / weight) if weight else 0
    frappe.db.set_value(
        "Project",
        project,
        {"percent_complete": percent_complete, "percent_complete_method": "Manual"},
        update_modified=False,
    )


def update_project_progress(doc, method=None):
    """Roll task progress up to the project AND every ancestor project.

    A parent project's progress blends its own direct tasks with each subproject's
    progress, weighted by the subproject's task count. Walking up the parent chain
    bottom-up means each ancestor reads its children's freshly-recomputed values.
    """
    if not doc.project:
        return
    # During a project cascade-delete, rows are being torn down — skip the churn.
    if frappe.flags.get("buildsuite_cascading"):
        return

    project = doc.project
    seen = set()
    while project and project not in seen:
        seen.add(project)
        _recompute_project_progress(project)
        project = frappe.db.get_value("Project", project, "parent_project")


import frappe
from frappe.utils import getdate, today


def update_delayed_tasks():
    current_date = getdate(today())

    # Rule 1:
    # End date passed and task not completed
    overdue_tasks = frappe.get_all(
        "Task",
        filters={
            "exp_end_date": ("<", current_date),
            "task_status": ("not in", ["Completed", "In Delay", "Blocked"]),
        },
        fields=["name"],
    )

    for task in overdue_tasks:
        task_doc = frappe.get_doc("Task", task.name)
        task_doc.task_status = "In Delay"
        task_doc.save(ignore_permissions=True)

    # Rule 2:
    # Start date passed but work not started
    not_started_tasks = frappe.get_all(
        "Task",
        filters={
            "exp_start_date": ("<", current_date),
            "task_status": ("not in", ["Completed", "In Progress", "In Delay", "Blocked"]),
        },
        fields=["name"],
    )

    for task in not_started_tasks:
        task_doc = frappe.get_doc("Task", task.name)
        task_doc.task_status = "In Delay"
        task_doc.save(ignore_permissions=True)

    frappe.db.commit()


# Native ERPNext status -> BuildSuite task_status (reverse of the sync in
# update_task_status). Used to backfill rows that predate the task_status field.
_STATUS_TO_TASK_STATUS = {
    "Completed": "Completed",
    "Working": "In Progress",
    "Overdue": "In Delay",
    "Open": "Yet To Start",
    "Pending Review": "In Progress",
    "Cancelled": "Yet To Start",
    "Template": "Yet To Start",
}


def backfill_task_status():
    """Populate task_status on Tasks where it's empty (idempotent).

    Tasks created before the task_status custom field existed have it blank, so
    the frontend (which now reads task_status) renders no status badge. Derive the
    value from progress first (100% -> Completed), then fall back to the native
    ERPNext status. Only touches rows with an empty task_status, so it's safe to
    re-run — it's wired into after_migrate so deployments self-heal.

    Returns the number of rows updated.
    """
    rows = frappe.get_all("Task", fields=["name", "status", "progress", "task_status"])
    updated = 0
    for row in rows:
        if row.task_status:
            continue
        if flt(row.progress) >= 100:
            new_status = "Completed"
        else:
            new_status = _STATUS_TO_TASK_STATUS.get(row.status, "Yet To Start")
        frappe.db.set_value("Task", row.name, "task_status", new_status, update_modified=False)
        updated += 1
    if updated:
        frappe.db.commit()
    return updated


# Activity / Milestone / Inspection per proposal §M2. The custom task_status-style
# Select drives BuildSuite workflow + Gantt rendering, independent of ERPNext's
# native `type` (Link -> Task Type) and `is_milestone` (Check).
_TASK_TYPE_VALUES = {"Activity", "Milestone", "Inspection"}


def backfill_task_type():
    """Populate task_type on Tasks where it's empty (idempotent). Reuse the legacy
    native `type` value when it already holds Activity/Milestone/Inspection;
    otherwise default to Activity."""
    rows = frappe.get_all("Task", fields=["name", "type", "task_type"])
    updated = 0
    for row in rows:
        if row.task_type:
            continue
        new_type = row.type if row.type in _TASK_TYPE_VALUES else "Activity"
        frappe.db.set_value("Task", row.name, "task_type", new_type, update_modified=False)
        updated += 1
    if updated:
        frappe.db.commit()
    return updated