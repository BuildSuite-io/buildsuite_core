"""Sales > Leads on existing sites: the Lead + UTM Source DocPerm matrix and the lead sources.

Permission setup is install-only (restore_role_permissions runs on install, not migrate), so a
site that already has BuildSuite gets the Lead grants here. The Lead Notes field and the LEAD-
naming series arrive with migrate's custom fields / property setters.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Lead"):
		return
	from buildsuite_core.install import seed_lead_sources
	from buildsuite_core.permissions.setup import setup_lead_permissions

	setup_lead_permissions()
	seed_lead_sources()
	frappe.clear_cache(doctype="Lead")
