# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Build a Letter Head per company from its branding (logo + subtext), so a printed document
carries the branding of the company that issued it. Supersedes the single shared "BuildSuite
Standard" head (which stays as the default company's, is_default — the fallback for documents
with no company). Idempotent — rebuilds are content-only overwrites."""

import frappe  # noqa: F401


def execute():
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		rebuild_all_letter_heads,
	)

	rebuild_all_letter_heads()
