# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Snapshot each BOQ Sub Item's native UOM from its Rate Master.

The `uom` field was added after these rows were created, so existing sub-items have
an empty unit and the BOQ tree falls back to the parent item's UOM. Backfill from the
linked Construction Rate Master so every component shows its own unit. Idempotent."""

import frappe


def execute():
	if not frappe.db.has_column("BOQ Sub Item", "uom"):
		return
	rows = frappe.get_all(
		"BOQ Sub Item",
		filters={"rate_master": ["is", "set"], "uom": ["in", ["", None]]},
		fields=["name", "rate_master"],
	)
	for r in rows:
		uom = frappe.db.get_value("Construction Rate Master", r.rate_master, "uom")
		if uom:
			frappe.db.set_value("BOQ Sub Item", r.name, "uom", uom, update_modified=False)
