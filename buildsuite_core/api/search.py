# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Backend for the SPA command palette (⌘K).

RECORDS reuse the SAME permission-safe search the Desk omnibar uses —
`frappe.utils.global_search.search` (the `__global_search` full-text index), which filters to the
doctypes the user can read AND per-document `has_permission()`. So the palette can never read a
record out of a doctype the user can't open.

DOCTYPES let a query name a doctype ("journal entry") and jump to its records via the generic
records browser (/records/<doctype>) — the universal fallback for any doctype the SPA has no
bespoke view for. Both are permission-gated; the frontend routes an app doctype's record to its
bespoke view and anything else to the generic view.
"""

import frappe
from frappe.utils.global_search import search as _global_search

# Framework / meta doctypes that are never useful as palette results.
_NOISE_DOCTYPES = {
	"DocType",
	"DocField",
	"DocPerm",
	"Custom DocPerm",
	"Custom Field",
	"Property Setter",
	"Client Script",
	"Server Script",
	"Report",
	"Workflow",
	"Workflow State",
	"Workflow Action Master",
	"Role",
	"Module Def",
	"Page",
	"Web Page",
	"Print Format",
	"Web Form",
	"Dashboard Chart",
	"Notification",
}

# App doctypes that already appear as their own (nicely-routed) palette "place" client-side — so
# the generic doctype-name search skips them and only offers the OTHER doctypes (Journal Entry,
# GL Entry, …). Mirrors permissions/resource_map.RESOURCE_DOCTYPES + the bespoke estimation ones.
_COVERED_DOCTYPES = {
	"Project", "Work Package", "Task", "Task Progress Entry", "Stage Planning", "Scope Change Order",
	"BOQ", "Assembly", "Estimate Template", "Construction Rate Master", "Tender", "Quotation",
	"Material Request", "Purchase Order", "Purchase Receipt", "Stock Entry", "Item",
	"Subcontractor Work Order", "Measurement Book", "Subcontractor Bill", "Supplier",
	"Employee", "Crew", "Field Attendance", "Machinery", "Machinery Usage",
	"Customer", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Petty Cash Request",
	"Expense Entry",
}


@frappe.whitelist()
def global_search(text: str, limit: int = 12):
	"""Permission-safe record matches for the palette. Returns [{doctype, name, title}], most
	relevant first; [] for a query under 2 chars. Any readable doctype (minus framework noise) —
	the frontend routes app doctypes to their bespoke view and the rest to the generic view."""
	text = (text or "").strip()
	limit = max(1, min(int(limit or 12), 25))
	if len(text) < 2:
		return []
	raw = _global_search(text, 0, max(limit * 3, 30)) or []
	out = []
	for row in raw:
		if row.get("doctype") in _NOISE_DOCTYPES:
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


@frappe.whitelist()
def search_doctypes(text: str, limit: int = 6):
	"""DocTypes whose name matches `text` and the user can read — palette "places" that open the
	doctype's generic list (/records/<doctype>). Excludes the app doctypes that already have their
	own place, framework noise, child tables and singles. Returns [{doctype, label}]."""
	text = (text or "").strip()
	limit = max(1, min(int(limit or 6), 12))
	if len(text) < 2:
		return []
	candidates = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0, "name": ["like", f"%{text}%"]},
		pluck="name",
		limit=60,
	)
	matched = [
		dt
		for dt in candidates
		if dt not in _NOISE_DOCTYPES and dt not in _COVERED_DOCTYPES and frappe.has_permission(dt, "read")
	]
	# Prefix matches first, then alphabetical.
	matched.sort(key=lambda d: (not d.lower().startswith(text.lower()), d))
	return [{"doctype": d, "label": d} for d in matched[:limit]]


@frappe.whitelist()
def command_palette(text: str, limit: int = 12):
	"""One round trip for the palette: name-matched doctypes (generic-list places) + content-matched
	records. Places (app lists + reports) are computed client-side; these are the backend parts."""
	return {
		"doctypes": search_doctypes(text, 6),
		"records": global_search(text, limit),
	}


# App record doctypes to enrol in the global-search index so their records are findable by content
# in the palette (Frappe only searches doctypes listed in Global Search Settings). The ERPNext
# defaults already cover Customer/Supplier/Sales Invoice/etc.; these are the app + finance ones
# that aren't. Add here to widen what a content search can find.
_GLOBAL_SEARCH_DOCTYPES = (
	"Project",
	"Work Package",
	"Task",
	"Stage Planning",
	"Scope Change Order",
	"BOQ",
	"Assembly",
	"Estimate Template",
	"Construction Rate Master",
	"Tender",
	"Quotation",
	"Material Request",
	"Purchase Order",
	"Purchase Receipt",
	"Subcontractor Work Order",
	"Measurement Book",
	"Subcontractor Bill",
	"Field Attendance",
	"Machinery",
	"Machinery Usage",
	"Crew",
	"Purchase Invoice",
	"Journal Entry",
	"Payment Entry",
	"Petty Cash Request",
	"Expense Entry",
)


def sync_global_search_doctypes():
	"""Enrol the app's record doctypes in Global Search Settings so the palette can find their
	records by content. Idempotent — adds only the missing ones and enqueues a one-time background
	reindex of just those (so a migrate is never blocked and configured doctypes aren't reprocessed)."""
	gss = frappe.get_single("Global Search Settings")
	existing = {r.document_type for r in gss.allowed_in_global_search}
	added = []
	for dt in _GLOBAL_SEARCH_DOCTYPES:
		if dt in existing or not frappe.db.exists("DocType", dt):
			continue
		gss.append("allowed_in_global_search", {"document_type": dt})
		added.append(dt)
	if not added:
		return []
	gss.flags.ignore_permissions = True
	gss.save()
	# Existing records aren't in the index until reindexed; do it off the migrate in the background.
	frappe.enqueue(
		"buildsuite_core.api.search.rebuild_global_search", doctypes=added, queue="long", timeout=1800
	)
	return added


def rebuild_global_search(doctypes):
	"""(Re)build the global-search index for each doctype. Enqueued by sync_global_search_doctypes;
	safe to call directly to reindex on demand."""
	from frappe.utils.global_search import rebuild_for_doctype

	for dt in doctypes or []:
		try:
			rebuild_for_doctype(dt)
			frappe.db.commit()
		except Exception:
			frappe.log_error(title=f"BuildSuite: global search reindex failed for {dt}"[:140])
