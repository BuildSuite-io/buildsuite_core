# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Company branding → Letter Head bridge.

Each company has its own Letter Head — a materialised snapshot of that company's logo +
subtext — so a printed document carries the branding of the company that issued it (the
default company's head is is_default, the fallback for documents with no company). This
doc_event rebuilds a company's letter head whenever it is saved, in Desk or via the SPA, so
print formats always show the current branding.
"""

import frappe  # noqa: F401 (kept for hook signature parity / future use)


def rebuild_letter_head_on_company_change(doc, method=None):
	"""Company.on_update hook: rebuild THIS company's letter head from its branding."""
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		rebuild_letter_head,
	)

	rebuild_letter_head(doc.name)
