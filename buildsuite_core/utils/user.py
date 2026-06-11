"""Keep a User's BuildSuite role in sync with their persona custom field.

Persona is a single-select, so exactly one BuildSuite role should follow it. We
run on `validate` (which fires on both insert and update) and mutate `doc.roles`
in place — that saves atomically with the user and avoids the recursive-save trap
that `add_roles`/`remove_roles` (which save the doc themselves) would cause.

Delete needs no handler: Frappe cascades the Has Role child rows when the User is
deleted.
"""

import frappe

from buildsuite_core.permissions.setup import PERSONA_TO_ROLE, BUILDSUITE_ROLES

# Roles fully owned by the persona field — at most one is present at a time and
# the rest are stripped so persona stays the single source of truth. System
# Manager is deliberately excluded: a persona can GRANT it, but this hook must
# never REVOKE it (that role is assigned for platform-admin reasons too).
_MANAGED_ROLES = set(BUILDSUITE_ROLES)


def sync_persona_roles(doc, method=None):
    if doc.name in ("Administrator", "Guest"):
        return

    desired = PERSONA_TO_ROLE.get((doc.persona or "").strip())

    kept = []
    have_desired = False
    for row in doc.roles:
        if row.role in _MANAGED_ROLES and row.role != desired:
            continue  # stale persona role — drop it
        if row.role == desired:
            have_desired = True
        kept.append(row)
    doc.roles = kept

    # Grant the persona's role (BuildSuite role or native System Manager). Guard
    # on existence so a not-yet-seeded role can't block the user save.
    if desired and not have_desired and frappe.db.exists("Role", desired):
        doc.append("roles", {"role": desired})
