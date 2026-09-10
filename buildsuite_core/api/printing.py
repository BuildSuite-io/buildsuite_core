# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Server-rendered print HTML for the SPA print views.

The Vue print views render whatever Frappe would render in Desk: the doctype's
DEFAULT Print Format (Customize Form → "Default Print Format") and the default (or
the document's own) Letter Head. So changing the default print format — or the letter
head — in Desk changes the SPA print view too, with no frontend change. Frappe's own
`get_html_and_style` does the resolution and enforces read permission
(`check_permission=True`); this is a thin, type-hinted wrapper that also returns the
resolved format name for display.
"""

import frappe
from frappe.utils import cint


@frappe.whitelist()
def get_print_html(
	doctype: str,
	name: str,
	print_format: str | None = None,
	letterhead: str | None = None,
	no_letterhead: int = 0,
	language: str | None = None,
) -> dict:
	"""Return ``{html, style, print_format}`` for a document's print view.

	``print_format`` unset → the doctype's ``meta.default_print_format`` (else
	"Standard"). ``letterhead`` unset → the document's ``letter_head`` field, else the
	``is_default`` Letter Head. Read permission is enforced by ``get_html_and_style``.
	"""
	from frappe.www.printview import get_html_and_style

	if language:
		frappe.local.lang = language

	result = get_html_and_style(
		doc=doctype,
		name=name,
		print_format=print_format,  # None → meta.default_print_format or "Standard"
		letterhead=letterhead,  # None → doc.letter_head or the is_default Letter Head
		no_letterhead=cint(no_letterhead),
		trigger_print=False,
	)

	resolved_format = print_format or frappe.get_meta(doctype).default_print_format or "Standard"
	return {
		"html": result.get("html"),
		"style": result.get("style"),
		"print_format": resolved_format,
	}
