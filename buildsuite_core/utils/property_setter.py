# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Property setters that are written only when they change.

frappe.make_property_setter always inserts a NEW Property Setter, and the Property Setter's own
validate deletes any existing one for the same doctype / field / property first. Called on every
migrate, that deletes and re-inserts each setter even when its value is the same — new names, a
cache clear per doctype, and a background job per delete (delete_dynamic_links).

ensure_property_setter looks first: the same value is left alone, a different value is updated
in place, and only a missing setter is created through Frappe.
"""

import frappe
from frappe.utils import cstr

UNCHANGED, UPDATED, CREATED = "unchanged", "updated", "created"


def _existing(doctype, doctype_or_field, property, fieldname=None):
	filters = {"doc_type": doctype, "property": property, "doctype_or_field": doctype_or_field}
	if doctype_or_field == "DocField":
		filters["field_name"] = fieldname
	return frappe.get_all(
		"Property Setter", filters=filters, fields=["name", "value", "property_type"], limit=1
	)


def ensure_property_setter(args, validate_fields_for_doctype=False, is_system_generated=True):
	"""Make a doctype/field property hold `args.value`, touching the database only when it must.

	`args` takes the keys frappe.make_property_setter does (doctype, fieldname, property, value,
	property_type, doctype_or_field). Returns "unchanged", "updated" or "created"."""
	args = frappe._dict(args)
	args.doctype_or_field = args.doctype_or_field or "DocField"
	# Frappe's own path for anything it would resolve itself: a setter across every doctype with
	# the field, or one whose property type it must look up.
	if not args.doctype or not args.property_type:
		frappe.make_property_setter(
			args,
			validate_fields_for_doctype=validate_fields_for_doctype,
			is_system_generated=is_system_generated,
		)
		return CREATED

	existing = _existing(args.doctype, args.doctype_or_field, args.property, args.fieldname)
	value = cstr(args.value)
	if existing:
		row = existing[0]
		if cstr(row.value) == value and row.property_type == args.property_type:
			return UNCHANGED
		doc = frappe.get_doc("Property Setter", row.name)
		doc.value = value
		doc.property_type = args.property_type
		doc.flags.validate_fields_for_doctype = validate_fields_for_doctype
		doc.save(ignore_permissions=True)  # not new, so Frappe keeps the row; clears the doctype cache
		return UPDATED

	# None yet (a setter's name is doctype-field-property, so there is never more than one).
	frappe.make_property_setter(
		args, validate_fields_for_doctype=validate_fields_for_doctype, is_system_generated=is_system_generated
	)
	return CREATED
