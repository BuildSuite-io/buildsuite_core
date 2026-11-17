# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Carry an installed app's Custom Fields through a bespoke save API.

Bespoke SPA forms save through whitelisted functions that copy named fields onto a document, so
a Custom Field an extension added would be dropped. These helpers close that gap safely:

    apply_custom_fields(doc, values)   # before doc.save(): sets only allowed Custom Fields
    custom_field_values(doc)           # when serializing: the values the form binds back

A key is applied only if it is a *Custom Field* of that DocType (never a standard field, so the
client cannot set owner, docstatus, amounts or anything the API computes), is a plain value
field (no tables or layout), is not read-only, and the user may write its permission level."""

import frappe
from frappe.model import no_value_fields


def _custom_fieldnames(doctype: str) -> set[str]:
	return set(frappe.get_all("Custom Field", filters={"dt": doctype}, pluck="fieldname"))


def _writable_fields(doctype: str):
	"""DocFields a client may set: the doctype's Custom Fields that are plain, editable values."""
	meta = frappe.get_meta(doctype)
	allowed_levels = set(meta.get_permlevel_access("write"))
	custom = _custom_fieldnames(doctype)
	return {
		df.fieldname: df
		for df in meta.fields
		if df.fieldname in custom
		and df.fieldtype not in no_value_fields
		and not df.read_only
		and (df.permlevel or 0) in allowed_levels
	}


def apply_custom_fields(doc, values) -> list[str]:
	"""Set the allowed Custom Field values on `doc` (not saved). Returns the fieldnames set."""
	values = frappe.parse_json(values) if isinstance(values, str) else values
	if not values or not isinstance(values, dict):
		return []
	allowed = _writable_fields(doc.doctype)
	applied = []
	for fieldname, value in values.items():
		if fieldname in allowed:
			doc.set(fieldname, value)
			applied.append(fieldname)
	return applied


def custom_field_values(doc) -> dict:
	"""The Custom Field values of `doc` the current user may read, keyed by fieldname."""
	meta = frappe.get_meta(doc.doctype)
	readable_levels = set(meta.get_permlevel_access("read"))
	custom = _custom_fieldnames(doc.doctype)
	return {
		df.fieldname: doc.get(df.fieldname)
		for df in meta.fields
		if df.fieldname in custom
		and df.fieldtype not in no_value_fields
		and (df.permlevel or 0) in readable_levels
	}
