# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Company branding → Letter Head bridge.

The shared "BuildSuite Standard" Letter Head (used by every print format) is a
materialised snapshot of the default company's logo + subtext. This doc_event rebuilds
it whenever the company is saved — in Desk or via the SPA — so print formats always show
the current branding.
"""

import frappe


def rebuild_letter_head_on_company_change(doc, method=None):
	"""Company.on_update hook: refresh the letter head from the default company's branding.

	Single-company seam — only the default company drives the (single, is_default) letter
	head, so a save on any other company is a no-op here.
	"""
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		rebuild_letter_head,
	)
	from buildsuite_core.utils.project import default_company

	if doc.name == default_company():
		rebuild_letter_head(doc.name)
