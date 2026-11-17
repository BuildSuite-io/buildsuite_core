# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Move each company's "Subcontractor Charges" account under "Direct Expenses".

It used to be created directly under the root "Expenses" group, beside Direct and Indirect
Expenses, so reports and accountants treated it as neither a direct nor an indirect cost. Only an
account still sitting on the root is moved: one an accountant has already placed (under Direct,
Indirect or anywhere else) is theirs and is left alone. Postings keep working; an account's id
does not change when it is moved."""

import frappe

ACCOUNT_NAME = "Subcontractor Charges"


def execute():
	for acc in frappe.get_all(
		"Account",
		filters={"account_name": ACCOUNT_NAME},
		fields=["name", "company", "parent_account"],
	):
		if not acc.parent_account or frappe.db.get_value("Account", acc.parent_account, "parent_account"):
			continue  # not directly on a root group: already placed by someone
		direct = frappe.db.get_value(
			"Account",
			{"account_name": "Direct Expenses", "company": acc.company, "is_group": 1},
			"name",
		)
		if not direct or direct == acc.parent_account:
			continue
		doc = frappe.get_doc("Account", acc.name)
		doc.parent_account = direct
		doc.flags.ignore_permissions = True
		doc.save()
