# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Backfill default roles onto personas that were created empty.

The persona-creation patches (repair_default_personas / enforce_persona_backend_only) run
BEFORE the BuildSuite roles exist — the roles are created later, by setup_record_permissions
via the resync_* patches — so personas were inserted with empty role tables. seed_personas
then skipped them (it only attaches roles to personas it creates itself, never to existing
ones), so those personas stayed role-less and their users were locked out of the app until an
admin added the roles by hand. The roles exist by now, so re-run repair_default_personas to
add the missing default roles. Idempotent; never removes an admin's extra roles."""


def execute():
	from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import (
		repair_default_personas,
	)

	repair_default_personas()
