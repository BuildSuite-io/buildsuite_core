def get_property_setters():
	return [
		{
			"name": "Project-status-options",
			"doctype_or_field": "DocField",
			"doctype": "Project",
			"fieldname": "status",
			"property": "options",
			"value": "Open\nWorking\nCompleted\nOn Hold\nCancelled",
			"property_type": "Text",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "status",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "status",
			"property": "in_list_view",
			"value": "0",
			"property_type": "Check",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "status",
			"property": "in_standard_filter",
			"value": "0",
			"property_type": "Check",
		},
		# Scheduling type now lives on the native `type` Link (-> Task Type). Default it
		# to "Activity" and surface it as a standard filter (parity with the removed
		# custom task_type Select).
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "type",
			"property": "default",
			"value": "Activity",
			"property_type": "Text",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "type",
			"property": "in_standard_filter",
			"value": "1",
			"property_type": "Check",
		},
	]
