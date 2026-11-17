"""Persona.project_visibility is new. Give every persona the project team scoping its users had
while that was hard-coded per role (permissions/project.py), so nobody's visibility changes on
migrate: the default personas take their seeded value, and any other persona the value its roles
gave it. From here on an admin sets it per persona.

Safe on a live site: it writes this one new field and nothing else — no DocPerm, role, user or
workspace record is touched — and the value it writes is the scoping each persona's users already
had, so what anyone sees is unchanged. It runs once; seeding never overwrites the field later."""

import frappe

from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import DEFAULT_PROJECT_VISIBILITY
from buildsuite_core.permissions.project import visibility_from_roles


def execute():
	if not frappe.db.has_column("Persona", "project_visibility"):
		return
	for persona in frappe.get_all("Persona", pluck="name"):
		visibility = DEFAULT_PROJECT_VISIBILITY.get(persona) or visibility_from_roles(
			frappe.get_all("Persona Role", filters={"parent": persona}, pluck="role")
		)
		frappe.db.set_value("Persona", persona, "project_visibility", visibility, update_modified=False)
