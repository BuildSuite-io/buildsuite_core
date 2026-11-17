"""Parse the dynamic "Add filter" tuples the SPA sends to server-paged list APIs."""

import json

import frappe
from frappe import _


def parse_list_filters(raw) -> list[list]:
	"""Return the SPA's Frappe filter tuples (`[[field, op, value], ...]`) from a JSON string.

	Only the shape is checked here; `frappe.get_list` validates the field names against the doctype
	and applies the caller's read permissions, so a filter can't reach what the user can't read.
	"""
	if not raw:
		return []
	try:
		filters = json.loads(raw) if isinstance(raw, str) else raw
	except ValueError:
		frappe.throw(_("Invalid filters."))
	if not isinstance(filters, list):
		frappe.throw(_("Invalid filters."))
	for f in filters:
		if not (isinstance(f, list) and len(f) == 3 and isinstance(f[0], str) and isinstance(f[1], str)):
			frappe.throw(_("Invalid filters."))
	return filters
