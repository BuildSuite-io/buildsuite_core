# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe

from buildsuite_core.report_access import reset_report_roles_to_matrix, seed_report_anchors


def execute():
	"""One-time re-baseline of every gated report's roles to the access matrix.

	The anchor seeder is create-if-missing (so an admin's later role edits survive migrate), which
	means a role change in _REPORT_ANCHORS never reaches a site that already has the anchor; and the
	file-based Script Reports carry their roles in their own .json. This patch converges BOTH —
	the bespoke anchors and the file-based reports — to the matrix on existing sites, once. Fresh
	installs get the matrix from the seeder + report .json and skip this patch. Idempotent:
	reset_report_roles_to_matrix() skips any report already correct."""
	seed_report_anchors()  # ensure anchors exist on older sites before re-roling
	changed = reset_report_roles_to_matrix()
	if changed:
		frappe.db.commit()  # nosemgrep
