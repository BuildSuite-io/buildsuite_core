import frappe
import json
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate, new_line_sep, nowdate

@frappe.whitelist()
def create_purchase_order(source_name, target_doc=None):
    doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Purchase Order",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["uom", "stock_uom"],
					["uom", "uom"],
					["sales_order", "sales_order"],
					["sales_order_item", "sales_order_item"],
					["wip_composite_asset", "wip_composite_asset"],
				],
				"postprocess": update_item,
                "condition": lambda doc: doc.ordered_qty < doc.qty,
			},
            
		},
		target_doc,
        
	)
    doclist.set_onload("load_after_mapping", False)
    return doclist

def update_item(obj, target, source_parent):
	target.conversion_factor = obj.conversion_factor
	target.qty = flt(flt(obj.stock_qty) - flt(obj.ordered_qty)) / target.conversion_factor
	target.stock_qty = target.qty * target.conversion_factor
	if getdate(target.schedule_date) < getdate(nowdate()):
		target.schedule_date = None