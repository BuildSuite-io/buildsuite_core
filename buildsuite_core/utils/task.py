import frappe
from frappe.utils import flt


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
