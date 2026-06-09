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
