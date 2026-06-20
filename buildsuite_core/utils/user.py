"""Keep a User's BuildSuite role in sync with their persona custom field.

Persona is a single-select, so exactly one BuildSuite role should follow it. We
run on `validate` (which fires on both insert and update) and mutate `doc.roles`
in place — that saves atomically with the user and avoids the recursive-save trap
that `add_roles`/`remove_roles` (which save the doc themselves) would cause.

Delete needs no handler: Frappe cascades the Has Role child rows when the User is
deleted.
"""

import frappe

from buildsuite_core.permissions.setup import (
	BUILDSUITE_ROLES,
	PERSONA_TO_ROLE,
	WORKFLOW_EDITOR_ROLE,
)

# Roles fully owned by the persona field — stripped when they no longer match the
# persona so it stays the single source of truth. The workflow-editor marker role
# rides along with any persona (needed for Stage Planning workflow editing).
# System Manager is deliberately excluded: a persona can GRANT it, but this hook
# must never REVOKE it (it's assigned for platform-admin reasons too).
_MANAGED_ROLES = set(BUILDSUITE_ROLES) | {WORKFLOW_EDITOR_ROLE}


def sync_persona_roles(doc, method=None):
	if doc.name in ("Administrator", "Guest"):
		return

	desired = PERSONA_TO_ROLE.get((doc.persona or "").strip())

	# Roles to keep/grant for the current persona.
	keep = set()
	if desired:
		keep.add(desired)
		keep.add(WORKFLOW_EDITOR_ROLE)

	kept, present = [], set()
	for row in doc.roles:
		if row.role in _MANAGED_ROLES and row.role not in keep:
			continue  # stale managed role — drop it
		kept.append(row)
		present.add(row.role)
	doc.roles = kept

	# Grant anything missing (guard on existence so a not-yet-seeded role can't
	# block the user save).
	for role in keep - present:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})
