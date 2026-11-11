# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Company branding → Letter Head bridge.

Each company has its own Letter Head — a materialised snapshot of that company's logo +
subtext — so a printed document carries the branding of the company that issued it (the
default company's head is is_default, the fallback for documents with no company). This
doc_event rebuilds a company's letter head whenever it is saved, in Desk or via the SPA, so
print formats always show the current branding.
"""

import frappe


def rebuild_letter_head_on_company_change(doc, method=None):
	"""Company.on_update hook: rebuild THIS company's letter head from its branding."""
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		rebuild_letter_head,
	)

	rebuild_letter_head(doc.name)


def rebuild_letter_head_after_company_rename(doc, method=None, old=None, new=None, merge=False):
	"""Company.after_rename hook: the letter head follows the company's name. A non-default
	company's head is named after the company, so rename leaves the old one behind: drop it
	(disable it if a document still points at it) and build the head under the new name. The
	default company keeps its fixed head, which is just rebuilt with the new name."""
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		letter_head_name,
		rebuild_letter_head,
	)

	new_name = new or doc.name
	stale = f"BuildSuite \u2014 {old}" if old else None
	if stale and stale != letter_head_name(new_name) and frappe.db.exists("Letter Head", stale):
		try:
			frappe.delete_doc("Letter Head", stale, ignore_permissions=True)
		except frappe.LinkExistsError:
			frappe.db.set_value("Letter Head", stale, "disabled", 1)
	rebuild_letter_head(new_name)
