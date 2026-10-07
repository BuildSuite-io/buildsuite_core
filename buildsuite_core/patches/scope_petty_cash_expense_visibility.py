# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Scope Petty Cash Request + Expense Entry visibility to the owner (if_owner), and hand `owner`
to the beneficiary on records raised on their behalf.

setup_petty_cash_permissions runs on after_install, not after_migrate, so existing sites need this
to pick up the new if_owner DocPerms (the four finance/admin roles + System Manager see all; every
other role sees only its own). It also backfills:
  - `raised_by` = the current owner (the real creator), for audit; and
  - `owner` = the beneficiary (Petty Cash `requested_by`; Expense `employee`'s linked User) on
    records where an approver created it for someone else — so if_owner now shows it to them.
Idempotent."""

import frappe

from buildsuite_core.permissions.setup import setup_petty_cash_permissions


def _rehome(doctype, rows, beneficiary_of):
	for r in rows:
		updates = {}
		if not r.get("raised_by"):
			updates["raised_by"] = r.owner  # keep the real creator before owner moves
		beneficiary = beneficiary_of(r)
		if beneficiary and beneficiary != r.owner and frappe.db.exists("User", beneficiary):
			updates["owner"] = beneficiary
		if updates:
			frappe.db.set_value(doctype, r.name, updates, update_modified=False)


def execute():
	# 1) Apply the if_owner DocPerms (see-all vs own-only).
	setup_petty_cash_permissions()

	# 2) Petty Cash Request — beneficiary is the holder (requested_by).
	_rehome(
		"Petty Cash Request",
		frappe.get_all("Petty Cash Request", fields=["name", "owner", "requested_by", "raised_by"]),
		lambda r: r.requested_by,
	)

	# 3) Expense Entry — beneficiary is the Employee's linked User.
	_rehome(
		"Expense Entry",
		frappe.get_all("Expense Entry", fields=["name", "owner", "employee", "raised_by"]),
		lambda r: frappe.db.get_value("Employee", r.employee, "user_id") if r.employee else None,
	)

	frappe.db.commit()
