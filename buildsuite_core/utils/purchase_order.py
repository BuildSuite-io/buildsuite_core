import frappe
import erpnext
import json
from erpnext.stock.get_item_details import _get_item_tax_template

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_tax_template(doctype, txt, searchfield, start, page_len, filters):
	item_doc = frappe.get_cached_doc("Item", filters.get("item_code"))
	item_group = filters.get("item_group")
	company = filters.get("company")
	taxes = item_doc.taxes or []

	while item_group:
		item_group_doc = frappe.get_cached_doc("Item Group", item_group)
		taxes += item_group_doc.taxes or []
		item_group = item_group_doc.parent_item_group

	if not taxes:
		return frappe.get_all("Item Tax Template", filters={"disabled": 0, "company": company,'custom_purpose':filters.get("custom_purpose")}, as_list=True)
	else:
		valid_from = filters.get("valid_from")
		valid_from = valid_from[1] if isinstance(valid_from, list) else valid_from

		args = {
			"item_code": filters.get("item_code"),
			"posting_date": valid_from,
			"tax_category": filters.get("tax_category"),
			"company": company,
            "custom_purpose":filters.get("custom_purpose"),
		}

		taxes = _get_item_tax_template(args, taxes, for_validate=True)
		return [(d,) for d in set(taxes)]