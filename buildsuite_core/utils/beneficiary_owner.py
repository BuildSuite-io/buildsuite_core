# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Beneficiary ownership for Petty Cash Request + Expense Entry.

The person a float / expense is FOR becomes the record's `owner`, so Frappe-native "Only If
Creator" (if_owner) DocPerms show it to them with no permission code — the client controls
visibility entirely from Role Permission Manager. The actual entry-maker is kept in `raised_by`.

Beneficiary:
  * Petty Cash Request — `requested_by` (a User)
  * Expense Entry      — the holder Employee's linked User (`employee.user_id`)

`owner` is handed over in after_insert, NOT before_insert, because Document.insert() force-sets
`owner = session.user` during the insert (frappe/model/document.py set_user_and_timestamp), so a
before_insert value is overwritten. `raised_by` is stamped before_insert while session.user is
still the creator.
"""

import frappe


def _beneficiary(doc):
	if doc.doctype == "Expense Entry":
		return frappe.db.get_value("Employee", doc.employee, "user_id") if doc.get("employee") else None
	if doc.doctype == "Petty Cash Request":
		return doc.get("requested_by")
	return None


def stamp_raised_by(doc, method=None):
	"""Record the real entry-maker before `owner` is handed to the beneficiary."""
	if not doc.get("raised_by"):
		doc.raised_by = frappe.session.user


def reassign_owner_to_beneficiary(doc, method=None):
	"""Hand `owner` to the beneficiary so native if_owner DocPerms scope to them. No-op when the
	beneficiary is the creator, unknown, or not a real User.

	The in-memory `owner` is updated alongside the DB so a later save of the same doc in the request
	(e.g. issue_direct creates then disburses) doesn't trip Frappe's "owner is a constant" check."""
	beneficiary = _beneficiary(doc)
	if beneficiary and beneficiary != doc.owner and frappe.db.exists("User", beneficiary):
		frappe.db.set_value(doc.doctype, doc.name, "owner", beneficiary, update_modified=False)
		doc.owner = beneficiary
