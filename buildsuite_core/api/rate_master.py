import json

import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def update_rates_from_po(purchase_order, updates, supplier=None):
	if isinstance(updates, str):
		updates = json.loads(updates)

	# The PO-submit rate-update dialog is gated to governance roles + the empowered
	# Procurement Officer (who is read-only on the Rate Master form). Enforced
	# server-side so it holds independent of the UI (PERM-013).
	from buildsuite_core.permissions.setup import RATE_UPDATE_GOVERNANCE_ROLES

	if not set(frappe.get_roles()) & set(RATE_UPDATE_GOVERNANCE_ROLES):
		frappe.throw(
			_("You are not permitted to update Rate Master rates."),
			frappe.PermissionError,
		)

	changed = []
	for row in updates:
		rate_master = row.get("rate_master")
		new_rate = flt(row.get("new_rate"))
		if not rate_master or new_rate <= 0:
			continue

		doc = frappe.get_doc("Construction Rate Master", rate_master)
		if flt(doc.current_rate) == new_rate:
			continue

		doc.flags.rate_source = {"purchase_order": purchase_order, "supplier": supplier}
		doc.current_rate = new_rate
		# The governance gate above authorises the write; the Rate Master form perm
		# (Procurement Officer = read-only) is deliberately bypassed for this path.
		doc.save(ignore_permissions=True)
		changed.append(rate_master)

	return changed
