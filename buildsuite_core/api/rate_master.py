import json

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def update_rates_from_po(purchase_order, updates, supplier=None):
	if isinstance(updates, str):
		updates = json.loads(updates)

	changed = []
	for row in updates:
		rate_master = row.get("rate_master")
		new_rate = flt(row.get("new_rate"))
		if not rate_master or new_rate <= 0:
			continue

		doc = frappe.get_doc("Construction Rate Master", rate_master)
		if not frappe.has_permission("Construction Rate Master", "write", doc=doc):
			frappe.throw(
				_("Not permitted to update Rate Master {0}.").format(rate_master),
				frappe.PermissionError,
			)
		if flt(doc.current_rate) == new_rate:
			continue

		doc.flags.rate_source = {"purchase_order": purchase_order, "supplier": supplier}
		doc.current_rate = new_rate
		doc.save()
		changed.append(rate_master)

	return changed
