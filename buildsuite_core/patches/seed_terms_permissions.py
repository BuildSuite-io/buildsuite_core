# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Apply the Terms & Conditions DocPerms to existing sites.

Full management for the admin / Accountant / Procurement Officer / Estimator roles (+ System
Manager); every other BuildSuite role gets `select` only. setup_record_permissions is install-only,
so existing sites need this one-time apply. Idempotent. The custom_applicable_for field itself syncs
via the after_migrate Custom Field hook."""

import frappe

from buildsuite_core.permissions.setup import setup_terms_permissions


def execute():
	if not frappe.db.exists("DocType", "Terms and Conditions"):
		return
	setup_terms_permissions()
	frappe.db.commit()
