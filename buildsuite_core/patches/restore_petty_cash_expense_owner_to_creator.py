# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Undo the `owner`-to-beneficiary reassignment from scope_petty_cash_expense_visibility.

That earlier change handed `owner` to the beneficiary so if_owner DocPerms would show a float to
the person it was raised for — but that broke Frappe's "Only If Creator" (if_owner) and "Created
By", because the real creator was no longer the owner. Visibility now lives in a
permission_query_conditions + has_permission hook (permissions/finance_access) that scopes on
owner OR beneficiary, so `owner` can go back to being the creator.

This re-applies the DocPerms (if_owner cleared) and restores `owner` = the creator, which the
earlier patch preserved in `raised_by`. Idempotent."""

import frappe

from buildsuite_core.permissions.setup import setup_petty_cash_permissions


def execute():
	# Re-apply DocPerms without if_owner (scoping is now the finance_access hook's job).
	setup_petty_cash_permissions()

	for doctype in ("Petty Cash Request", "Expense Entry"):
		if not frappe.get_meta(doctype).has_field("raised_by"):
			continue
		for r in frappe.get_all(
			doctype, filters={"raised_by": ["is", "set"]}, fields=["name", "owner", "raised_by"]
		):
			if r.raised_by and r.owner != r.raised_by:
				frappe.db.set_value(doctype, r.name, "owner", r.raised_by, update_modified=False)

	frappe.db.commit()
