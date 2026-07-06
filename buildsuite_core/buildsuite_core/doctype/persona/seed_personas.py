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

# (persona_name, slug, sort_order, (roles…), backend_only)
# persona_name doubles as the record name (autoname field:persona_name), so existing
# User.persona string values resolve straight to these Link targets — no data migration.
# backend_only=1 personas are assignable only from the Frappe desk, never the app's
# user forms (the two admin personas — they grant platform-admin access).
PERSONAS = (
	("Director / Owner", "director", 1, ("BuildSuite Director",), 0),
	("Project Manager", "pm", 2, ("BuildSuite PM",), 0),
	("Estimator", "estimator", 3, ("BuildSuite Estimator",), 0),
	("Quantity Surveyor", "qs", 4, ("BuildSuite QS",), 0),
	("Site Engineer", "site-engineer", 5, ("BuildSuite Site Engineer",), 0),
	("Foreman / Supervisor", "foreman", 6, ("BuildSuite Foreman",), 0),
	("Procurement Officer", "procurement", 7, ("BuildSuite Procurement Officer",), 0),
	("Store Keeper", "store-keeper", 8, ("BuildSuite Store Keeper",), 0),
	("Accountant", "accountant", 9, ("BuildSuite Accountant",), 0),
	("HR Manager", "hr-manager", 10, ("BuildSuite HR Manager",), 0),
	("System Manager (Admin)", "admin", 11, ("System Manager",), 1),
	("BuildSuite Administrator", "bsa", 12, ("BuildSuite Administrator",), 1),
)


def seed_personas():
	"""Create any missing default persona. Idempotent; leaves existing personas
	(and any admin edits to them) untouched."""
	created = []
	for persona_name, slug, order, roles, backend_only in PERSONAS:
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
				"backend_only": backend_only,
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


def _repair_existing(persona_name, slug, roles, backend_only):
	"""Re-enable a default persona, restore its default roles and enforce its
	backend-only flag. Returns True if it changed. Never removes an admin's extra
	roles."""
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
	if int(doc.backend_only or 0) != backend_only:
		doc.backend_only = backend_only
		changed = True
	changed = _add_missing_roles(doc, roles) or changed
	if changed:
		doc.flags.ignore_permissions = True
		doc.save()
	return changed


def repair_default_personas():
	"""Restore the default personas to a working state: create any that are missing,
	re-enable any that were left disabled, add back any default role rows that went
	missing, and enforce the admin personas' backend-only flag. Recovers sites where
	the two admin personas ended up disabled (dropping them from the user-form picker
	and locking admins out of Settings).

	Only ever creates, enables, adds roles and fixes the backend-only flag — never
	removes an admin's extra roles or personas — so it's safe to re-run."""
	repaired = []
	for persona_name, slug, order, roles, backend_only in PERSONAS:
		if frappe.db.exists("Persona", persona_name):
			if _repair_existing(persona_name, slug, roles, backend_only):
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
				"backend_only": backend_only,
			}
		)
		for role in roles:
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role})
		doc.insert(ignore_permissions=True)
		repaired.append(persona_name)
	return repaired
