# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Mirror read to child tables on existing sites.

Custom DocPerms override standard perms, so a BuildSuite role granted read on a parent doctype
gets nothing on that parent's child (Table) doctypes — a list/detail view that fetches child
rows directly then 403s (e.g. HR Manager on Crew Member). setup_child_table_read_access() runs
on install; this applies the same grant to already-migrated sites."""

import frappe

from buildsuite_core.permissions.setup import setup_child_table_read_access


def execute():
	setup_child_table_read_access()
	frappe.clear_cache()
