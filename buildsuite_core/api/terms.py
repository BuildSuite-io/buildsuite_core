# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Terms & Conditions library for the SPA settings screen.

Uses Frappe's native `Terms and Conditions` doctype — `terms` is a Text Editor (rich text, so
tables and formatting work), and `custom_applicable_for` (BuildSuite custom field) tags each clause
with the document it belongs to (Quotation, Purchase Order, …) so the settings screen can segregate
the library by that reference. Visibility is native DocPerms: the admin / finance / procurement /
estimation roles manage the library; every other role gets `select` only (pick a clause on a
document, never manage it here).
"""

import frappe
from frappe import _
from frappe.utils import cint

DOCTYPE = "Terms and Conditions"

# The documents a clause can apply to — the segregation categories on the settings screen. Keep in
# sync with the custom_applicable_for Select options (custom_property_list/custom_field.py).
APPLICABLE_FOR = [
	"Quotation",
	"Tender",
	"Request for Quotation",
	"Purchase Order",
	"Subcontractor Work Order",
	"Subcontractor Bill",
	"Sales Invoice",
	"Purchase Invoice",
]
_BUYING = {
	"Request for Quotation",
	"Purchase Order",
	"Purchase Invoice",
	"Subcontractor Work Order",
	"Subcontractor Bill",
}
_SELLING = {"Quotation", "Tender", "Sales Invoice"}


@frappe.whitelist()
def terms_access():
	"""The current user's access to the terms library + the categories to segregate by."""
	return {
		"can_read": bool(frappe.has_permission(DOCTYPE, "read")),
		"can_write": bool(frappe.has_permission(DOCTYPE, "write")),
		"can_create": bool(frappe.has_permission(DOCTYPE, "create")),
		"can_delete": bool(frappe.has_permission(DOCTYPE, "delete")),
		"applicable_for": APPLICABLE_FOR,
	}


@frappe.whitelist()
def list_terms():
	"""Every clause the user may see, for the settings screen. Full-access roles see the whole
	library; a select-only role has no read perm and gets an empty list (it picks clauses on
	documents, it doesn't manage them here)."""
	if not frappe.has_permission(DOCTYPE, "read"):
		return []
	return frappe.get_list(
		DOCTYPE,
		fields=[
			"name",
			"title",
			"custom_applicable_for",
			"custom_is_default",
			"terms",
			"disabled",
			"modified",
		],
		order_by="custom_applicable_for asc, title asc",
		limit_page_length=0,
	)


@frappe.whitelist()
def save_terms(
	name: str | None = None,
	title: str | None = None,
	applicable_for: str | None = None,
	terms: str | None = None,
	disabled: int | str = 0,
	is_default: int | str = 0,
):
	"""Create / update a clause. `terms` is rich-text HTML (native Text Editor field). `is_default`
	makes it the clause a new document of its kind starts with; only one per kind is."""
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the clause a name — it's what the picker shows."))
	applicable_for = applicable_for or None

	if name and frappe.db.exists(DOCTYPE, name):
		doc = frappe.get_doc(DOCTYPE, name)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc(DOCTYPE)
		doc.check_permission("create")

	doc.title = title
	doc.custom_applicable_for = applicable_for
	doc.terms = terms or ""
	doc.disabled = 1 if cint(disabled) else 0
	doc.custom_is_default = 1 if cint(is_default) and applicable_for else 0
	# Keep the native pickers working: a clause is offered on a transaction only when its
	# buying/selling flag matches, so derive them from the chosen document.
	doc.buying = 1 if applicable_for in _BUYING else 0
	doc.selling = 1 if applicable_for in _SELLING else 0
	doc.save()
	if doc.custom_is_default:
		# One default per kind: the others of the same kind stop being offered first.
		for other in frappe.get_all(
			DOCTYPE,
			filters={
				"custom_applicable_for": applicable_for,
				"custom_is_default": 1,
				"name": ["!=", doc.name],
			},
			pluck="name",
		):
			frappe.db.set_value(DOCTYPE, other, "custom_is_default", 0)
	return {"name": doc.name, "title": doc.title}


@frappe.whitelist()
def default_terms(applicable_for: str):
	"""The clause a new document of this kind starts with (its "offer this one first" clause),
	if one is set, enabled and readable by the user: {name, terms}, or None."""
	rows = frappe.get_list(
		DOCTYPE,
		filters={"custom_applicable_for": applicable_for, "custom_is_default": 1, "disabled": 0},
		fields=["name", "terms"],
		limit_page_length=1,
	)
	return rows[0] if rows else None


@frappe.whitelist()
def delete_terms(name: str):
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("delete")
	frappe.delete_doc(DOCTYPE, name)
	return {"ok": True}
