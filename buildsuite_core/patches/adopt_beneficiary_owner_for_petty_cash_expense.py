# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Beneficiary-owner model for Petty Cash Request + Expense Entry.

Hand `owner` to the beneficiary — the person the float / expense is FOR — so Frappe-native
"Only If Creator" (if_owner) DocPerms scope visibility to them, with NO permission hook (the
finance_access permission_query_conditions + has_permission hooks are removed). The real
entry-maker is preserved in `raised_by`.

Beneficiary: Petty Cash `requested_by`; Expense the holder Employee's linked User.

Re-applies the petty-cash / expense DocPerms (now carrying if_owner on the own-scoped roles) and
backfills existing rows: raised_by ← the current owner (creator) where empty, then owner ← the
beneficiary. Idempotent — safe to re-run. Supersedes restore_petty_cash_expense_owner_to_creator.
"""

import frappe

from buildsuite_core.permissions.setup import setup_petty_cash_permissions


def _beneficiary(doctype, row):
	if doctype == "Expense Entry":
		return frappe.db.get_value("Employee", row.employee, "user_id") if row.get("employee") else None
	return row.get("requested_by")


def execute():
	# Re-apply DocPerms: own-scoped roles now carry if_owner (visibility is native, not a hook).
	setup_petty_cash_permissions()

	specs = {
		"Petty Cash Request": ["name", "owner", "raised_by", "requested_by"],
		"Expense Entry": ["name", "owner", "raised_by", "employee"],
	}
	for doctype, fields in specs.items():
		if not frappe.get_meta(doctype).has_field("raised_by"):
			continue
		for r in frappe.get_all(doctype, fields=fields):
			# 1. Preserve the creator: owner is still the creator pre-migration.
			if not r.raised_by:
				frappe.db.set_value(doctype, r.name, "raised_by", r.owner, update_modified=False)
			# 2. Hand owner to the beneficiary (if there is one, and it's a real User).
			beneficiary = _beneficiary(doctype, r)
			if beneficiary and beneficiary != r.owner and frappe.db.exists("User", beneficiary):
				frappe.db.set_value(doctype, r.name, "owner", beneficiary, update_modified=False)

	frappe.db.commit()
