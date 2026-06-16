"""Schedule graph API for the Gantt + the dependency cycle guard.

Dependencies are stored on ERPNext's native Task.depends_on child table, whose
`task` field is the PREDECESSOR, enriched with custom fields dependency_type
(FS/SS/FF) and lag_days (Slice 1.1 Bit 1). Successors are inferred (reverse the
edge set), never stored. See context/scheduler-gantt-plan.md.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_project_schedule(project):
    """Return the schedule graph for a project: every task with its scheduling
    fields and its PREDECESSOR edges. Successors are inferred client-side by
    reversing the edge set. Respects Task read permission (uses get_list).
    """
    if not project:
        frappe.throw(_("project is required"))

    tasks = frappe.get_list(
        "Task",
        filters={"project": project},
        fields=[
            "name", "subject",
            "type as task_type", "task_status",
            "exp_start_date", "exp_end_date", "progress", "work_package", "project",
        ],
        order_by="exp_start_date asc, creation asc",
        limit_page_length=0,
    )

    task_names = [t.name for t in tasks]
    for t in tasks:
        t["predecessors"] = []

    if task_names:
        by_name = {t.name: t for t in tasks}
        edges = frappe.get_all(
            "Task Depends On",
            filters={"parent": ["in", task_names], "parenttype": "Task"},
            fields=["parent", "task as predecessor", "dependency_type", "lag_days"],
        )
        for e in edges:
            parent = by_name.get(e.parent)
            # Only attach edges whose predecessor is also in this project's set;
            # cross-project edges are out of scope for the single-project Gantt.
            if parent is not None and e.predecessor in by_name:
                parent["predecessors"].append({
                    "task": e.predecessor,
                    "dependency_type": e.dependency_type or "FS",
                    "lag_days": e.lag_days or 0,
                })

    return {"project": project, "tasks": tasks}


# --- cycle guard --------------------------------------------------------------

def validate_task_dependencies(doc, method=None):
    """Task validate hook: reject a depends_on edge that would create a cycle
    (a task depending, transitively, on itself)."""
    for row in (doc.depends_on or []):
        predecessor = row.task
        if not predecessor:
            continue
        if predecessor == doc.name:
            frappe.throw(_("A task cannot depend on itself."))
        if _creates_cycle(doc.name, predecessor):
            frappe.throw(
                _("Dependency on {0} would create a circular schedule.").format(predecessor)
            )


def _creates_cycle(task_name, predecessor_name, _seen=None):
    """True if `task_name` is already a (transitive) predecessor of
    `predecessor_name` — so adding the edge predecessor_name -> task_name closes a
    loop. Walks UP the depends_on graph from predecessor_name over stored edges.
    """
    if not task_name or not predecessor_name:
        return False
    if predecessor_name == task_name:
        return True
    if _seen is None:
        _seen = set()
    if predecessor_name in _seen:
        return False
    _seen.add(predecessor_name)

    upstream = frappe.get_all(
        "Task Depends On",
        filters={"parent": predecessor_name, "parenttype": "Task"},
        pluck="task",
    )
    for p in upstream:
        if _creates_cycle(task_name, p, _seen):
            return True
    return False
