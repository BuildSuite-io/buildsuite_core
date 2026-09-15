"""Sanitize the ad-hoc "+ Add filter" tuples the SPA's DeskList sends.

Server-paginated list views hand the built-in dynamic-filter builder's tuples straight to
their whitelisted list endpoint. Those tuples are user-supplied, so before they reach
frappe.get_list they're validated here: each must be a ``[field, operator, value]`` list
with a known operator, and any field that isn't a real fieldname on the doctype is dropped.
frappe.get_list parameterizes the values, so this guards shape + surface, not SQL injection.
"""

import json

import frappe

# The operators DeskFilterEditor / toServerFilter can emit. Anything else is dropped.
ALLOWED_OPERATORS = {
	"=", "!=", "like", "not like", "in", "not in", "is",
	">", "<", ">=", "<=", "between", "timespan",
}


def parse_client_filters(raw, doctype: str) -> list:
	"""Return a clean list of ``[field, operator, value]`` filters, or ``[]``.

	Anything malformed — bad JSON, wrong shape, unknown operator, or a field that isn't a
	real fieldname on ``doctype`` (or the always-present ``name``) — is silently skipped so
	one bad chip can't break the whole list.
	"""
	if not raw:
		return []
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except (ValueError, TypeError):
			return []
	if not isinstance(raw, list):
		return []

	meta = frappe.get_meta(doctype)
	valid_fields = {df.fieldname for df in meta.fields}
	valid_fields.update({"name", "owner", "creation", "modified", "modified_by", "docstatus"})

	out = []
	for row in raw:
		if not isinstance(row, (list, tuple)) or len(row) != 3:
			continue
		field, operator, value = row
		if not isinstance(field, str) or field not in valid_fields:
			continue
		if not isinstance(operator, str) or operator.lower() not in ALLOWED_OPERATORS:
			continue
		out.append([field, operator.lower(), value])
	return out
