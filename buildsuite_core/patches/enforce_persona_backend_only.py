# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Mark the two admin personas ("System Manager (Admin)", "BuildSuite Administrator")
as backend-only so the BuildSuite app's user forms stop offering them — they grant
platform-admin access and should only be assigned from the Frappe desk. Reuses the
idempotent default-persona repair, which now also enforces the backend_only flag."""

import frappe


def execute():
	from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import (
		repair_default_personas,
	)

	repair_default_personas()
	frappe.db.commit()
