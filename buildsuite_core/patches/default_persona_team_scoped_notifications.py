# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Persona.team_scoped_notifications is new: seed it from each persona's project visibility (on for
a persona scoped to its teams' projects, off for one that sees all projects). Only personas whose
flag is still at its 0 default are set, and the setting does nothing until a workflow is marked
"Team-scoped notifications"."""

import frappe

from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import default_team_scoped_notifications


def execute():
	if not frappe.get_meta("Persona").has_field("team_scoped_notifications"):
		return
	for p in frappe.get_all(
		"Persona", filters={"team_scoped_notifications": 0}, fields=["name", "project_visibility"]
	):
		if default_team_scoped_notifications(p.project_visibility):
			frappe.db.set_value("Persona", p.name, "team_scoped_notifications", 1, update_modified=False)
