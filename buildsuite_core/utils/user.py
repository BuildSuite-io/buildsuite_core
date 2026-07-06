"""Keep a User's BuildSuite roles in sync with their Persona.

Persona is now a Link to the Persona master, whose `roles` child table lists the
roles a user with that persona should hold. We run on `validate` (which fires on
both insert and update) and mutate `doc.roles` in place — that saves atomically
with the user and avoids the recursive-save trap that `add_roles`/`remove_roles`
(which save the doc themselves) would cause.

The persona owns the roles it grants: any persona-managed role that no longer
matches the current persona is stripped, so the persona stays the single source of
truth. Protected native roles (System Manager, Administrator) are never stripped —
a persona may GRANT System Manager, but platform admins hold it for other reasons
and this hook must not revoke it.

Delete needs no handler: Frappe cascades the Has Role child rows when the User is
deleted.
"""

import frappe

from buildsuite_core.permissions.setup import WORKFLOW_EDITOR_ROLE

# Native roles a persona may grant but this hook must never revoke.
PROTECTED_ROLES = {"System Manager", "Administrator", "All", "Guest"}


def _persona_roles(persona):
	"""Roles granted by a persona (its Persona Role child rows)."""
	if not persona:
		return set()
	return set(frappe.get_all("Persona Role", filters={"parent": persona}, pluck="role"))


def _managed_roles():
	"""Every role any persona grants (plus the workflow-editor marker), minus the
	protected native roles. These are the roles the persona field owns and may
	strip when they no longer match."""
	roles = set(frappe.get_all("Persona Role", pluck="role"))
	roles.add(WORKFLOW_EDITOR_ROLE)
	return roles - PROTECTED_ROLES


def sync_persona_roles(doc, method=None):
	if doc.name in ("Administrator", "Guest"):
		return

	# During install/migrate the Persona table may not exist yet — skip quietly.
	if not frappe.db.table_exists("Persona Role"):
		return

	desired = _persona_roles(doc.persona)

	# Roles to keep/grant for the current persona (grants may include a protected
	# role like System Manager; stripping below never touches protected roles).
	keep = set()
	if desired:
		keep |= desired
		keep.add(WORKFLOW_EDITOR_ROLE)

	managed = _managed_roles()

	kept, present = [], set()
	for row in doc.roles:
		if row.role in managed and row.role not in keep:
			continue  # stale persona-managed role — drop it
		kept.append(row)
		present.add(row.role)
	doc.roles = kept

	# Grant anything missing (guard on existence so a not-yet-seeded role can't
	# block the user save).
	for role in keep - present:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
