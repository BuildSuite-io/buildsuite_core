# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Grant Item Group `select` to the Item-accessible BuildSuite roles on existing sites.

Item Group backs the Item form's item_group picker (and item-group filters), but natively only
ERPNext roles read it, so a BuildSuite persona (Procurement Officer, Store Keeper, Estimator, …) had
no grant and the picker 403'd. setup_record_permissions is install-only, so existing sites need this
one-time apply. Re-runs the authoritative purchase/stock permission setup (idempotent), which now
also grants Item Group `select` to every role that has Item access."""

import frappe

from buildsuite_core.permissions.setup import setup_purchase_stock_permissions


def execute():
	if not frappe.db.exists("DocType", "Item Group"):
		return
	setup_purchase_stock_permissions()
	frappe.db.commit()
