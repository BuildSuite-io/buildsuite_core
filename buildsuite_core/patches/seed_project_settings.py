# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Seed the Project Settings tab template on existing sites (the install seeder isn't re-run on
	migrate). Create-if-missing, so an admin's edits are left alone. The doctype schema is created by
	migrate before this post-model-sync patch runs."""
	from buildsuite_core.api.project_settings import seed_project_settings

	seed_project_settings()
	frappe.db.commit()  # nosemgrep
