# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Records side of the SPA command palette (⌘K).

Reuses the SAME permission-safe search the Desk omnibar uses —
`frappe.utils.global_search.search`, which reads the `__global_search` full-text index and filters
to (a) the doctypes the user can read and (b) per-document `has_permission()`. So a role that can't
open a doctype's list can't read its records out of the palette either — the rule the prototype's
search engine calls out (S363).

Global search indexes many off-topic doctypes (Warehouse, Account, User, Item Price, …); we keep
only the app's record doctypes — the ones with a SPA detail view (the frontend maps each to its
route). Navigation "places" (lists + reports) stay client-side, gated by the SPA's own permissions.
"""

import frappe
from frappe.utils.global_search import search as _global_search

# App record doctypes surfaced in the palette. These are the doctypes the SPA can open — a bespoke
# detail view (frontend DOCTYPE_META) OR the generic records browser (/records/<doctype>/<name>,
# gated by permissions.resource_map.RESOURCE_DOCTYPES). Anything else global search indexes
# (Warehouse, Account, User, …) is dropped as off-topic. Keep in sync with data/search.js.
SEARCHABLE_DOCTYPES = {
	# --- site execution ---
	"Project",
	"Work Package",
	"Task",
	"Task Progress Entry",
	"Stage Planning",
	"Scope Change Order",
	# --- estimation ---
	"BOQ",
	"Assembly",
	"Estimate Template",
	"Construction Rate Master",
	"Tender",
	"Quotation",
	# --- procurement ---
	"Material Request",
	"Purchase Order",
	"Purchase Receipt",
	"Stock Entry",
	"Item",
	# --- subcontract ---
	"Subcontractor Work Order",
	"Measurement Book",
	"Subcontractor Bill",
	"Supplier",
	# --- workforce / equipment ---
	"Employee",
	"Crew",
	"Field Attendance",
	"Machinery",
	"Machinery Usage",
	# --- project finance ---
	"Customer",
	"Sales Invoice",
	"Purchase Invoice",
	"Payment Entry",
	"Petty Cash Request",
	"Expense Entry",
}


@frappe.whitelist()
def global_search(text: str, limit: int = 12):
	"""Permission-safe record matches for the command palette, narrowed to the app's doctypes.

	Returns [{doctype, name, title}], most relevant first. Empty for a query under 2 chars."""
	text = (text or "").strip()
	limit = max(1, min(int(limit or 12), 25))
	if len(text) < 2:
		return []

	# Over-fetch, then keep only the app doctypes — global search ranks across everything the user
	# can read, so a fetch of `limit` alone could be all off-topic rows (e.g. Warehouses).
	raw = _global_search(text, 0, max(limit * 4, 40)) or []
	out = []
	for row in raw:
		if row.get("doctype") not in SEARCHABLE_DOCTYPES:
			continue
		out.append(
			{
				"doctype": row.get("doctype"),
				"name": row.get("name"),
				"title": row.get("title") or row.get("name"),
			}
		)
		if len(out) >= limit:
			break
	return out
