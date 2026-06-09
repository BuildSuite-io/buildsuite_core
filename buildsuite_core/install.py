import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from buildsuite_core.custom_property_list.custom_field import CUSTOM_FIELD
from buildsuite_core.custom_property_list.property_field import get_property_setters


def after_migrate():
    print(_("Creating Custom Fields..."))
    create_custom_fields(CUSTOM_FIELD, ignore_validate=True)
    make_property_setters()


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
