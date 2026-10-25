# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Grant Item `select` + `read` to the Foreman on existing sites.

ITEM_ROLE_PERMS now lists the Foreman explicitly (it was previously only layered on by the mobile
permissions). Record permissions are seeded on install only, so existing sites re-apply the Item
matrix here, then re-layer the mobile grants (Site Engineer keeps its Item select + read)."""

import frappe

from buildsuite_core.permissions.setup import setup_mobile_permissions, setup_purchase_stock_permissions


def execute():
	if not frappe.db.exists("DocType", "Item"):
		return
	setup_purchase_stock_permissions()
	setup_mobile_permissions()
	frappe.db.commit()
