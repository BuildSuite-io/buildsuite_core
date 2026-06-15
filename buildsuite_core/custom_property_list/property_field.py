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
        },
        {
            "doctype_or_field": "DocField",
            "doctype": "Task",
            "fieldname": "status",
            "property": "hidden",
            "value": "1",
            "property_type": "Check"
        },
        {
            "doctype_or_field": "DocField",
            "doctype": "Task",
            "fieldname": "status",
            "property": "in_list_view",
            "value": "0",
            "property_type": "Check"
        },
        {
            "doctype_or_field": "DocField",
            "doctype": "Task",
            "fieldname": "status",
            "property": "in_standard_filter",
            "value": "0",
            "property_type": "Check"
        },
    ]
