"""Seed BuildSuite Project Templates from the prototype's project-type templates.

Mirrors the prototype `projectTypeTemplates.js` shape, reconciled to the backend
doctype model chosen in design:

  BuildSuite Project Template
    project_type  -> Project Type (must already exist)
    stage_plans[] -> Stage Plan Template (one per stage)
        Stage Plan Template.tasks[] -> Stage Plan Task Template
            task -> Task (is_template = 1)   # ERPNext-native template task, cloned on instantiate

The prototype keys tasks by Work Package, while a Stage Plan Template groups tasks
under a Stage. For each template below the tasks are pre-mapped into stages by the
WP<->stage name correspondence (e.g. WP-FND -> Foundation). Stages with no matching
WP carry no tasks (e.g. Commercial "Substructure").

Idempotent: re-running reuses existing Stage Plan Templates (matched by name) and
the BuildSuite Project Template (matched by name). Template Tasks are created fresh
per Stage Plan Template (so identical subjects across templates — e.g. "Painting"
in both Commercial and Residential — keep their own per-template hours); the
Stage-Plan-Template-exists guard is what makes a re-run a no-op.

Run:
  bench --site <site> execute \
    buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.seed_templates.seed_all
  # or a single type:
  bench --site <site> execute \
    buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.seed_templates.seed_template \
    --kwargs "{'type_name': 'Commercial'}"
"""

import frappe

# Stage names are GLOBAL (Stage Plan Template autonames on stage_name), so they are
# prefixed with the type to stay unique across templates. The instantiated Stage
# Planning inherits this name via create_stage_plan().
TEMPLATES = {
    "Commercial": {
        "project_type": "Commercial",
        "stages": [
            {"stage_name": "Foundation", "tasks": [
                {"subject": "Earthwork excavation", "priority": "High", "expected_time": 240},
                {"subject": "PCC laying", "priority": "Medium", "expected_time": 120},
                {"subject": "Raft foundation casting", "priority": "High", "expected_time": 400},
            ]},
            {"stage_name": "Substructure", "tasks": []},
            {"stage_name": "Superstructure", "tasks": [
                {"subject": "Column casting - Level 1 to 5", "priority": "High", "expected_time": 800},
                {"subject": "Slab casting - Level 1 to 5", "priority": "High", "expected_time": 720},
            ]},
            {"stage_name": "MEP rough-in", "tasks": [
                {"subject": "Electrical conduit laying", "priority": "Medium", "expected_time": 320},
                {"subject": "Plumbing rough-in", "priority": "Medium", "expected_time": 280},
            ]},
            {"stage_name": "Finishing", "tasks": [
                {"subject": "Internal plaster", "priority": "Medium", "expected_time": 360},
                {"subject": "Floor tiling", "priority": "Medium", "expected_time": 240},
                {"subject": "Painting", "priority": "Low", "expected_time": 180},
            ]},
            {"stage_name": "Handover", "tasks": [
                {"subject": "Snagging walkthrough", "priority": "High", "expected_time": 40},
                {"subject": "Occupancy certificate", "priority": "High", "expected_time": 20},
            ]},
        ],
    },
    "Residential": {
        "project_type": "Residential",
        "stages": [
            {"stage_name": "Foundation", "tasks": [
                {"subject": "Earthwork excavation", "priority": "High", "expected_time": 200},
                {"subject": "Raft foundation casting", "priority": "High", "expected_time": 360},
            ]},
            {"stage_name": "Substructure", "tasks": []},
            {"stage_name": "Superstructure", "tasks": [
                {"subject": "Tower column casting", "priority": "High", "expected_time": 720},
                {"subject": "Tower slab casting", "priority": "High", "expected_time": 640},
            ]},
            {"stage_name": "MEP rough-in", "tasks": [
                {"subject": "Conduit + plumbing per unit", "priority": "Medium", "expected_time": 480},
            ]},
            # WP-AMEN (Amenities) has no dedicated stage in the prototype — folded
            # into Finishing (clubhouse / landscaping are finishing-phase work).
            {"stage_name": "Finishing", "tasks": [
                {"subject": "Wall plaster + putty", "priority": "Medium", "expected_time": 320},
                {"subject": "Floor tiling per unit", "priority": "Medium", "expected_time": 280},
                {"subject": "Joinery + kitchen fit-out", "priority": "Medium", "expected_time": 360},
                {"subject": "Painting", "priority": "Low", "expected_time": 200},
                {"subject": "Clubhouse finishing", "priority": "Medium", "expected_time": 240},
                {"subject": "Landscaping", "priority": "Low", "expected_time": 160},
            ]},
            {"stage_name": "Handover", "tasks": []},
        ],
    },
    "Infrastructure": {
        "project_type": "Infrastructure",
        "stages": [
            {"stage_name": "Site Prep", "tasks": [
                {"subject": "Site grading", "priority": "High", "expected_time": 320},
                {"subject": "Utility diversion", "priority": "High", "expected_time": 240},
            ]},
            {"stage_name": "Foundation", "tasks": [
                {"subject": "Pile installation", "priority": "High", "expected_time": 800},
                {"subject": "Pile cap casting", "priority": "High", "expected_time": 400},
            ]},
            {"stage_name": "Structure", "tasks": [
                {"subject": "Column casting", "priority": "High", "expected_time": 960},
                {"subject": "Deck casting", "priority": "High", "expected_time": 720},
                {"subject": "Retaining wall construction", "priority": "Medium", "expected_time": 540},
            ]},
            {"stage_name": "Finishing & Commissioning", "tasks": [
                {"subject": "Signalling fit-out", "priority": "High", "expected_time": 480},
                {"subject": "Testing & commissioning", "priority": "High", "expected_time": 320},
            ]},
        ],
    },
}


def _create_template_task(subject, priority="Medium", expected_time=0):
    """Create an ERPNext-native template Task (is_template=1). Called only from the
    guarded Stage-Plan-Template creation path, so re-runs don't duplicate."""
    task = frappe.new_doc("Task")
    task.subject = subject
    task.is_template = 1
    task.priority = priority
    task.expected_time = expected_time
    task.insert(ignore_permissions=True)
    return task.name


def _ensure_stage_plan_template(stage_plan_name, task_rows):
    """Find or create a Stage Plan Template with its task child rows."""
    if frappe.db.exists("Stage Plan Template", stage_plan_name):
        return stage_plan_name
    doc = frappe.new_doc("Stage Plan Template")
    doc.stage_name = stage_plan_name
    for t in task_rows:
        task_name = _create_template_task(
            t["subject"], t.get("priority", "Medium"), t.get("expected_time", 0)
        )
        doc.append("tasks", {"task": task_name, "subject": t["subject"]})
    doc.insert(ignore_permissions=True)
    return doc.name


def seed_template(type_name):
    """Create (idempotently) one BuildSuite Project Template for the given type."""
    spec = TEMPLATES.get(type_name)
    if not spec:
        frappe.throw(f"No seed template defined for type '{type_name}'")

    project_type = spec["project_type"]
    if not frappe.db.exists("Project Type", project_type):
        frappe.throw(f"Project Type '{project_type}' does not exist — create it first")

    # Build the Stage Plan Templates (prefixed names keep them globally unique).
    stage_plan_names = []
    for stage in spec["stages"]:
        prefixed = f"{type_name} - {stage['stage_name']}"
        stage_plan_names.append(
            _ensure_stage_plan_template(prefixed, stage["tasks"])
        )

    # The BuildSuite Project Template itself (template_name is the autoname).
    if frappe.db.exists("BuildSuite Project Template", type_name):
        tpl = frappe.get_doc("BuildSuite Project Template", type_name)
        tpl.set("stage_plans", [])
    else:
        tpl = frappe.new_doc("BuildSuite Project Template")
        tpl.template_name = type_name

    tpl.project_type = project_type
    for sp in stage_plan_names:
        tpl.append("stage_plans", {"stage_plan": sp})
    tpl.save(ignore_permissions=True)

    # No explicit commit — the caller (install/migrate hook, or `bench execute`)
    # owns the transaction.
    return tpl.name


def seed_all():
    """Seed every template defined in TEMPLATES."""
    created = [seed_template(name) for name in TEMPLATES]
    print("Seeded BuildSuite Project Templates:", created)
    return created
