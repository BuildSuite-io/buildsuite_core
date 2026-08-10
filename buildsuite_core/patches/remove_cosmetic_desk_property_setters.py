# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Remove the cosmetic (Desk-presentation) Property Setters this app used to ship.

BuildSuite renders its own forms in the Vue app, so it never needed to reshape the
native ERPNext Desk forms. Hiding standard fields / reordering forms / trimming list
views globally was intrusive for companies that use BuildSuite from the Desk alongside
other apps, so those setters were dropped from custom_property_list/property_field.py.
This patch deletes the ones already applied on existing sites, restoring the native
Desk presentation. Functional setters (option values, business-rule flags) are kept and
re-applied by after_migrate, so they are intentionally NOT listed here.

Each entry is matched exactly by (doc_type, field_name, property); a None field_name is
a doctype-level setter (e.g. field_order), whose Property Setter row has an empty
field_name.
"""

import frappe

# (doc_type, field_name, property) — field_name None = doctype-level setter.
COSMETIC = [
	("Material Request", "naming_series", "hidden"),
	("Material Request", "scan_barcode", "hidden"),
	("Material Request", "set_from_warehouse", "hidden"),
	("Material Request", "set_warehouse", "hidden"),
	("Material Request", "set_warehouse", "in_list_view"),
	("Material Request Item", "description", "in_list_view"),
	("Purchase Invoice", None, "field_order"),
	("Purchase Invoice", "currency_and_price_list", "hidden"),
	("Purchase Invoice", "incoterm", "hidden"),
	("Purchase Invoice", "naming_series", "hidden"),
	("Purchase Invoice", "scan_barcode", "hidden"),
	("Purchase Invoice", "shipping_rule", "hidden"),
	("Purchase Invoice", "update_stock", "hidden"),
	("Purchase Invoice Item", "uom", "in_list_view"),
	("Purchase Order", None, "field_order"),
	("Purchase Order", "currency_and_price_list", "hidden"),
	("Purchase Order", "naming_series", "hidden"),
	("Purchase Receipt", None, "field_order"),
	("Purchase Receipt", "apply_putaway_rule", "hidden"),
	("Purchase Receipt", "currency_and_price_list", "hidden"),
	("Purchase Receipt", "incoterm", "hidden"),
	("Purchase Receipt", "naming_series", "hidden"),
	("Purchase Receipt", "scan_barcode", "hidden"),
	("Purchase Receipt", "shipping_rule", "hidden"),
	("Purchase Receipt Item", "uom", "in_list_view"),
	("Stock Entry", None, "field_order"),
	("Stock Entry", "accounting_dimensions_section", "hidden"),
	("Stock Entry", "add_to_transit", "hidden"),
	("Stock Entry", "additional_costs_section", "depends_on"),
	("Stock Entry", "apply_putaway_rule", "hidden"),
	("Stock Entry", "bom_info_section", "depends_on"),
	("Stock Entry", "items_section", "depends_on"),
	("Stock Entry", "more_info", "depends_on"),
	("Stock Entry", "printing_settings", "depends_on"),
	("Stock Entry", "sb0", "depends_on"),
	("Stock Entry", "scan_barcode", "hidden"),
	("Stock Entry", "section_break_19", "depends_on"),
	("Stock Entry", "section_break_jwgn", "depends_on"),
	("Stock Entry Detail", "s_warehouse", "in_list_view"),
	("Stock Entry Detail", "t_warehouse", "in_list_view"),
	("Stock Entry Detail", "uom", "in_list_view"),
	("Task", "status", "hidden"),
	("Task", "status", "in_list_view"),
	("Task", "status", "in_standard_filter"),
	("Task", "type", "in_standard_filter"),
]


def execute():
	for doc_type, field_name, prop in COSMETIC:
		filters = {"doc_type": doc_type, "property": prop}
		if field_name is None:
			frappe.db.delete("Property Setter", {**filters, "field_name": ["in", ["", None]]})
		else:
			frappe.db.delete("Property Setter", {**filters, "field_name": field_name})
		frappe.clear_cache(doctype=doc_type)
