import frappe


def get_property_setters():
    return [
        {
            "name": "Project-status-options",
            "doctype_or_field": "DocField",
            "doctype": "Project",
            "fieldname": "status",
            "property": "options",
            "value": "Open\nWorking\nCompleted\nOn Hold\nCancelled",
            "property_type": "Text"
        }
    ]