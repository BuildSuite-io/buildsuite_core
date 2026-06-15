import frappe
from frappe.utils import flt
import json

def _wp_progress_from_tasks(tasks):
    if not tasks:
        return 0
    avg = sum(flt(t.get("progress", 0)) for t in tasks) / len(tasks)
    return min(avg, 100)


def update_work_package_progress(doc, method=None):
    if not doc.work_package:
        return

    tasks = frappe.get_all(
        "Task",
        filters={"work_package": doc.work_package},
        fields=["progress"],
    )
    frappe.db.set_value(
        "Work Package", doc.work_package, "progress", _wp_progress_from_tasks(tasks)
    )


def recalculate_work_package_on_task_trash(doc, method=None):
    """on_trash fires before the row is removed, so exclude the deleted task explicitly."""
    if not doc.work_package:
        return

    tasks = frappe.get_all(
        "Task",
        filters={"work_package": doc.work_package, "name": ("!=", doc.name)},
        fields=["progress"],
    )
    frappe.db.set_value(
        "Work Package", doc.work_package, "progress", _wp_progress_from_tasks(tasks)
    )

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


@frappe.whitelist()
def update_project_progress(doc, method=None):
    if not doc.project:
        return

    # Get all task progress values for the project
    tasks = frappe.get_all(
        "Task",
        filters={"project": doc.project},
        fields=["progress"]
    )

    task_count = len(tasks)

    if task_count == 0:
        percent_complete = 0
    else:
        total_progress = sum(flt(task.progress) for task in tasks)
        percent_complete = total_progress / task_count

    # Update the project
    proj = frappe.get_doc("Project", doc.project)

    # Avoid triggering unnecessary validations/hooks
    proj.percent_complete = percent_complete
    proj.percent_complete_method = "Manual"
    proj.save(ignore_permissions=True)
    proj.reload()


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