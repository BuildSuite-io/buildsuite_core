"""Keep a User's BuildSuite roles in sync with their Persona.

Persona is a Link to the Persona master, whose `roles` child table lists the roles
a user with that persona should hold. We run on `validate` (which fires on both
insert and update) and mutate `doc.roles` in place — that saves atomically with the
user and avoids the recursive-save trap that `add_roles`/`remove_roles` (which save
the doc themselves) would cause.

The sync is **additive**: setting a persona GRANTS its roles, but roles that were
added on top of a persona — whether native or BuildSuite-custom — are always kept.
A user with combined responsibilities (e.g. a PM who is also a Site Engineer) is a
legitimate flow, so manual additions must never be silently reverted.

The only roles ever removed are the ones the *previous* persona granted that the
new persona no longer grants, and only when the persona actually CHANGES — so
switching persona doesn't leave the old persona's roles piled on, while a plain
save (persona unchanged) strips nothing. A role a persona GRANTS is stripped when
you leave that persona even if it is System Manager (the "System Manager (Admin)"
persona grants it) — otherwise switching an admin down to a field persona would
silently leave platform-admin rights behind. Only two things are always kept: the
Frappe-internal roles (Administrator, All, Guest), and any role added MANUALLY on
top of a persona (a manual add is never in the previous persona's grant set, so it
is never eligible for stripping).

Delete needs no handler: Frappe cascades the Has Role child rows when the User is
deleted.
"""

import frappe

from buildsuite_core.permissions.setup import WORKFLOW_EDITOR_ROLE

# Frappe-internal roles this hook must never revoke on a persona switch. System Manager is
# deliberately NOT here: the "System Manager (Admin)" persona grants it, so leaving that persona
# must be able to strip it — like any other persona-granted role. A System Manager role added
# MANUALLY on top of a field persona still survives (only the previous persona's own grants are
# ever eligible for stripping), so this set only needs Frappe's own housekeeping roles.
PROTECTED_ROLES = {"Administrator", "All", "Guest"}


def _persona_roles(persona):
	"""Roles a persona grants (its Persona Role child rows) plus the workflow-editor
	marker that every BuildSuite persona carries."""
	if not persona:
		return set()
	roles = set(frappe.get_all("Persona Role", filters={"parent": persona}, pluck="role"))
	if roles:
		roles.add(WORKFLOW_EDITOR_ROLE)
	return roles


def sync_persona_roles(doc, method=None):
	if doc.name in ("Administrator", "Guest"):
		return

	# During install/migrate the Persona table may not exist yet — skip quietly.
	if not frappe.db.table_exists("Persona Role"):
		return

	# A set-but-unknown persona (dangling link to a Persona that isn't there) must
	# not strip the user's roles — that could silently unmake an admin. Leave roles
	# untouched until the persona resolves.
	if doc.persona and not frappe.db.exists("Persona", doc.persona):
		return

	grant = _persona_roles(doc.persona)

	# On a persona SWITCH, strip only the roles the previous persona granted that the
	# new persona no longer grants — never protected roles, never manual additions.
	before = doc.get_doc_before_save()
	old_persona = before.persona if before else None
	strip = set()
	if old_persona and old_persona != doc.persona:
		strip = (_persona_roles(old_persona) - grant) - PROTECTED_ROLES

	kept, present = [], set()
	for row in doc.roles:
		if row.role in strip:
			continue  # role from the previous persona, not re-granted — drop it
		kept.append(row)
		present.add(row.role)
	doc.roles = kept

	# Grant anything the current persona adds that isn't present yet (guard on
	# existence so a not-yet-seeded role can't block the user save).
	for role in grant - present:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
