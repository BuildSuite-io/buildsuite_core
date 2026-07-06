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
	"""Create any missing default persona. Idempotent; leaves existing personas
	(and any admin edits to them) untouched."""
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


def _add_missing_roles(doc, roles):
	"""Append any default role the persona is missing (existing role rows kept)."""
	have = {r.role for r in doc.roles}
	added = False
	for role in roles:
		if role not in have and frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
			added = True
	return added


def _repair_existing(persona_name, slug, roles):
	"""Re-enable a default persona and restore its default roles. Returns True if it
	changed. Never removes an admin's extra roles."""
	doc = frappe.get_doc("Persona", persona_name)
	changed = False
	if not doc.enabled:
		doc.enabled = 1
		changed = True
	if not doc.is_default:
		doc.is_default = 1
		changed = True
	if not (doc.slug or "").strip():
		doc.slug = slug
		changed = True
	changed = _add_missing_roles(doc, roles) or changed
	if changed:
		doc.flags.ignore_permissions = True
		doc.save()
	return changed


def repair_default_personas():
	"""Restore the default personas to a working state: create any that are missing,
	re-enable any that were left disabled, and add back any default role rows that
	went missing. This recovers sites where the two admin personas ended up disabled
	(dropping them from the user-form picker and locking admins out of Settings).

	Only ever creates, enables and ADDS roles — never removes an admin's extra roles
	or personas — so it's safe to re-run."""
	repaired = []
	for persona_name, slug, order, roles in PERSONAS:
		if frappe.db.exists("Persona", persona_name):
			if _repair_existing(persona_name, slug, roles):
				repaired.append(persona_name)
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
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role})
		doc.insert(ignore_permissions=True)
		repaired.append(persona_name)
	return repaired
