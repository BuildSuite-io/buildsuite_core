# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Timesheets now have their own SPA screens and a built-in Workforce shortcut, so drop the generic
"Timesheets" Records tile that seed_workforce_timesheet_tile added (it would open the plain records
view next to the real one). Only that tile is removed; other Records tiles are left alone."""

import frappe


def execute():
	settings = frappe.get_single("Workspace Setting")
	keep = [
		r for r in settings.doctypes if not (r.workspace == "workforce" and r.document_type == "Timesheet")
	]
	if len(keep) == len(settings.doctypes):
		return
	settings.set("doctypes", [{**r.as_dict(), "name": None} for r in keep])
	settings.flags.ignore_permissions = True
	settings.save()
