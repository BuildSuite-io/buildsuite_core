# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Grant Account `select` + `read` to Site Engineer / Foreman / Procurement Officer on existing sites.

These roles raise Expense Entries and so must resolve + view an Account in the expense_account
picker, but previously had no Account DocPerm. setup_record_permissions is install-only, so existing
sites need this one-time apply. Re-runs the authoritative petty-cash permission setup (idempotent),
which now also layers the three roles' select+read onto Account."""

import frappe

from buildsuite_core.permissions.setup import setup_petty_cash_permissions


def execute():
	if not frappe.db.exists("DocType", "Account"):
		return
	setup_petty_cash_permissions()
	frappe.db.commit()
