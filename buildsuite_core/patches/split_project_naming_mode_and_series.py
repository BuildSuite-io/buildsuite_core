# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Naming was originally a single Data field holding either "Project ID" or
a naming-series string. It's now a Select mode ("Project ID" | "Name Series") plus a
separate "Project Naming Series" field. Migrate any stored series string into the new
shape so existing sites keep naming projects the same way."""

import frappe

PROJECT_ID_MODE = "Project ID"
NAME_SERIES_MODE = "Name Series"
SETTINGS = "BuildSuite Core Settings"


def execute():
	current = frappe.db.get_single_value(SETTINGS, "project_naming")
	if not current or current in (PROJECT_ID_MODE, NAME_SERIES_MODE):
		return  # already in the new shape (or unset → default Project ID)

	# A legacy series string (e.g. "PROJ-.####") → Name Series mode + that series.
	doc = frappe.get_single(SETTINGS)
	doc.project_naming = NAME_SERIES_MODE
	doc.project_naming_series = current
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.db.commit()
