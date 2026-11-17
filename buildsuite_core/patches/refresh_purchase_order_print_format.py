# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Ship the Purchase Order print format that carries the company's address / GSTIN / CIN / phone /
email in "Ordered by" and prints the order's own Terms & conditions properly.

The seed only creates the format when it is missing, so a site that already has it keeps the old
layout. Replace it here, but only when it is still exactly what the app last seeded: a format an
admin has edited in Desk is theirs and is left alone."""

import hashlib

import frappe

FORMAT = "Purchase Order"
# sha1 of the html the app seeded before this patch
PREVIOUS_SEED_SHA1 = "4c95c9b0bf74b0c0ef1b188cea519a5d0051b984"


def execute():
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import _PO_PRINT_HTML

	html = frappe.db.get_value("Print Format", FORMAT, "html")
	if html is None:
		return
	if hashlib.sha1(html.encode()).hexdigest() != PREVIOUS_SEED_SHA1:
		return
	frappe.db.set_value("Print Format", FORMAT, "html", _PO_PRINT_HTML)
