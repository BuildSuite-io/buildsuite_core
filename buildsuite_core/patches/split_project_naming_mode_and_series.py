# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Naming was originally a single Data field holding either "Project ID" or
a naming-series string. It's now a Select MODE only ("Project ID" | "Name Series") —
the specific series is chosen per-project on the New Project form. Map any legacy
series string to "Name Series" so existing sites keep generating series-based names."""

import frappe

PROJECT_ID_MODE = "Project ID"
NAME_SERIES_MODE = "Name Series"
SETTINGS = "BuildSuite Core Settings"


def execute():
	current = frappe.db.get_single_value(SETTINGS, "project_naming")
	if not current or current in (PROJECT_ID_MODE, NAME_SERIES_MODE):
		return  # already in the new shape (or unset → default Project ID)

	# A legacy series string (e.g. "PROJ-.####") just means Name Series mode now.
	frappe.db.set_single_value(SETTINGS, "project_naming", NAME_SERIES_MODE)
	frappe.db.commit()
