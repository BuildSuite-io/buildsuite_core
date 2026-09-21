# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the Subcontract module masters — Construction Trades and Work Order Delivery
Types. Idempotent; run from install.after_install / after_migrate."""

import frappe

TRADES = (
	"Earthwork",
	"Concreting",
	"Masonry",
	"Structural Steel",
	"Plastering",
	"Flooring",
	"Tiling",
	"Waterproofing",
	"Painting",
	"Carpentry",
	"Electrical",
	"Plumbing",
	"HVAC",
	"False Ceiling",
	"Landscaping",
)

# (delivery_type, description)
DELIVERY_TYPES = (
	("Labour-only", "Subcontractor supplies labour; materials by the main contractor."),
	("Full sub", "Subcontractor supplies both labour and materials."),
)


def seed_construction_trades():
	created = []
	for trade in TRADES:
		if not frappe.db.exists("Construction Trade", trade):
			frappe.get_doc(
				{"doctype": "Construction Trade", "trade_name": trade, "enabled": 1}
			).insert(ignore_permissions=True)
			created.append(trade)
	return created


def seed_delivery_types():
	created = []
	for name, desc in DELIVERY_TYPES:
		if not frappe.db.exists("Subcontract Delivery Type", name):
			frappe.get_doc(
				{
					"doctype": "Subcontract Delivery Type",
					"delivery_type": name,
					"description": desc,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
			created.append(name)
	return created


def seed_subcontractor_supplier_group():
	"""A 'Subcontractor' Supplier Group so subcontractor Suppliers group cleanly. Idempotent.

	On a bare site the app can be installed BEFORE ERPNext's setup wizard seeds the Supplier Group
	tree — so there is no parent group to attach to, and the old fallback to the literal
	"All Supplier Groups" root failed with "Could not find Parent Supplier Group: All Supplier
	Groups". Attach under the standard ERPNext root when it exists, else any existing group, else
	create the root so the new group always has a valid parent."""
	if frappe.db.exists("Supplier Group", "Subcontractor"):
		return
	ROOT = "All Supplier Groups"
	parent = (
		ROOT
		if frappe.db.exists("Supplier Group", ROOT)
		else frappe.db.get_value("Supplier Group", {"is_group": 1}, "name")
	)
	if not parent:
		# Empty tree (setup wizard hasn't run) — create the standard root; ERPNext's own
		# install_fixtures is a no-op on it later since it already exists.
		frappe.get_doc(
			{"doctype": "Supplier Group", "supplier_group_name": ROOT, "is_group": 1}
		).insert(ignore_permissions=True)
		parent = ROOT
	frappe.get_doc(
		{"doctype": "Supplier Group", "supplier_group_name": "Subcontractor", "parent_supplier_group": parent}
	).insert(ignore_permissions=True)


def seed_subcontract_masters():
	seed_construction_trades()
	seed_delivery_types()
	seed_subcontractor_supplier_group()

	# Print assets — default Letter Head + the Subcontractor Work Order Print Format.
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		seed_print_assets,
	)

	seed_print_assets()
