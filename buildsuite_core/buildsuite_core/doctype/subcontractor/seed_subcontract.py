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


def seed_subcontract_masters():
	seed_construction_trades()
	seed_delivery_types()

	# Print assets — default Letter Head + the Subcontractor Work Order Print Format.
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		seed_print_assets,
	)

	seed_print_assets()
