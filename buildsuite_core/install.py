import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from buildsuite_core.custom_property_list.custom_field import CUSTOM_FIELD
from buildsuite_core.custom_property_list.property_field import get_property_setters
from buildsuite_core.permissions.setup import setup_record_permissions


def after_install():
    seed_master_data()
    setup_record_permissions()


def after_migrate():
    print(_("Creating Custom Fields..."))
    create_custom_fields(CUSTOM_FIELD, ignore_validate=True)
    make_property_setters()
    seed_master_data()
    setup_record_permissions()


def seed_master_data():
    project_types = [
        "Commercial", "Residential", "Infrastructure",
        "Industrial", "Renovation", "Interior", "Other",
    ]
    for pt in project_types:
        if not frappe.db.exists("Project Type", pt):
            frappe.get_doc({"doctype": "Project Type", "project_type": pt}).insert(ignore_permissions=True)

    # Task Type uses Prompt autoname (the type name IS the record name) and has no
    # `task_type` field — set the name directly.
    task_types = ["Activity", "Milestone", "Inspection"]
    for tt in task_types:
        if not frappe.db.exists("Task Type", tt):
            frappe.get_doc({"doctype": "Task Type", "name": tt}).insert(ignore_permissions=True)

    # Project Templates (Commercial / Residential / Infrastructure) — depend on the
    # Project Types seeded above. Idempotent (Stage-Plan-Template-exists guard).
    from buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.seed_templates import seed_all
    seed_all()


def before_migrate():
    delete_custom_fields(CUSTOM_FIELD)


def delete_custom_fields(custom_fields):
    for doctypes, fields in custom_fields.items():
        if isinstance(fields, dict):
            fields = [fields]

        if isinstance(doctypes, str):
            doctypes = (doctypes,)

        for doctype in doctypes:
            frappe.db.delete(
                "Custom Field",
                {
                    "fieldname": ("in", [field["fieldname"] for field in fields]),
                    "dt": doctype,
                },
            )

            frappe.clear_cache(doctype=doctype)


def make_property_setters():
    for property_setter in get_property_setters():
        frappe.make_property_setter(property_setter, validate_fields_for_doctype=False)
