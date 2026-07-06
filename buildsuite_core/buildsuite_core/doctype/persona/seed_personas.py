# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the default BuildSuite Personas and their role mappings.

Replaces the hardcoded PERSONA_TO_ROLE dict: each persona is now a Persona record
whose `roles` child table drives which roles a user with that persona is granted
(the User.validate hook reads it). Idempotent — run from install.after_install /
after_migrate, after the roles themselves are ensured. Re-running only fills in a
missing persona; it never overwrites an admin's later edits to an existing one.
"""

import frappe

# (persona_name, slug, sort_order, (roles…))
# persona_name doubles as the record name (autoname field:persona_name), so existing
# User.persona string values resolve straight to these Link targets — no data migration.
PERSONAS = (
	("Director / Owner", "director", 1, ("BuildSuite Director",)),
	("Project Manager", "pm", 2, ("BuildSuite PM",)),
	("Estimator", "estimator", 3, ("BuildSuite Estimator",)),
	("Quantity Surveyor", "qs", 4, ("BuildSuite QS",)),
	("Site Engineer", "site-engineer", 5, ("BuildSuite Site Engineer",)),
	("Foreman / Supervisor", "foreman", 6, ("BuildSuite Foreman",)),
	("Procurement Officer", "procurement", 7, ("BuildSuite Procurement Officer",)),
	("Store Keeper", "store-keeper", 8, ("BuildSuite Store Keeper",)),
	("Accountant", "accountant", 9, ("BuildSuite Accountant",)),
	("HR Manager", "hr-manager", 10, ("BuildSuite HR Manager",)),
	("System Manager (Admin)", "admin", 11, ("System Manager",)),
	("BuildSuite Administrator", "bsa", 12, ("BuildSuite Administrator",)),
)


def seed_personas():
	created = []
	for persona_name, slug, order, roles in PERSONAS:
		if frappe.db.exists("Persona", persona_name):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Persona",
				"persona_name": persona_name,
				"slug": slug,
				"sort_order": order,
				"enabled": 1,
				"is_default": 1,
			}
		)
		for role in roles:
			# Guard so a not-yet-seeded role can't block persona creation.
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role})
		doc.insert(ignore_permissions=True)
		created.append(persona_name)
	return created
