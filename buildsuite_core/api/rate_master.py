import json

import frappe
from frappe import _
from frappe.utils import cint, flt


@frappe.whitelist()
def list_rate_masters(start=0, page_length=10, search=None, category=None, with_counts=False):
	"""One page of rate masters + total_count (filtered, for the pager). When
	with_counts is set, also the global total and per-category counts (KPI cards)."""
	filters = {}
	if category:
		filters["category"] = category
	or_filters = None
	if search:
		or_filters = [
			["rate_code", "like", f"%{search}%"],
			["rate_name", "like", f"%{search}%"],
		]

	rows = frappe.get_list(
		"Construction Rate Master",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name", "rate_code", "rate_name", "category", "uom",
			"current_rate", "previous_rate", "effective_date", "modified_by",
		],
		order_by="rate_code asc",
		start=cint(start),
		page_length=cint(page_length),
	)
	total_count = frappe.get_list(
		"Construction Rate Master",
		filters=filters,
		or_filters=or_filters,
		fields=[{"COUNT": "name", "as": "count"}],
	)[0].count

	result = {"rows": rows, "total_count": total_count}

	# Global counts (whole catalog) change only on add/edit/delete, not on paging or
	# search — so the client asks for them once on load + after mutations, not per page.
	if cint(with_counts):
		cat_rows = frappe.get_list(
			"Construction Rate Master",
			fields=["category", {"COUNT": "name", "as": "count"}],
			group_by="category",
		)
		result["total"] = sum(r.count for r in cat_rows)
		result["category_counts"] = {r.category: r.count for r in cat_rows}

	return result


@frappe.whitelist()
def get_rate_update_threshold():
	"""PO-submit rate-prompt threshold (%) from Core Settings; 5.0 if unset."""
	raw = frappe.db.get_single_value("BuildSuite Core Settings", "rate_master_update_threshold")
	return flt(raw) if raw else 5.0


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
