"""Re-apply the full persona permission matrix so imported/existing sites converge.

setup_record_permissions() is install-only, so imported / live-data sites carry STALE DocPerms:
personas hit "no permission" / "insufficient permission" on entities the CURRENT matrix grants
(Task create, Material Consumption via Stock Entry, Supplier/Customer read, ...), even though a
freshly-installed site is correct. Re-run the authoritative setup to refresh every persona's
DocPerms in one pass. Idempotent — a no-op where the matrix is already current.
"""

import frappe


def execute():
	from buildsuite_core.permissions.setup import setup_record_permissions

	setup_record_permissions()
	frappe.clear_cache()
	print("resync_persona_permission_matrix: re-applied the persona DocPerm matrix")
