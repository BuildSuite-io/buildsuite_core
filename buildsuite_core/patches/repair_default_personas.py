# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Repair the default Personas on sites where the two admin personas ended up
disabled — which dropped them from the user-form persona picker (an enabled-only
list) and could leave an admin without the BuildSuite Administrator role, locking
them out of Settings. Ensures all default personas exist, are enabled and carry
their default roles. Safe and idempotent."""

import frappe


def execute():
	from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import (
		repair_default_personas,
	)

	repair_default_personas()
	frappe.db.commit()
