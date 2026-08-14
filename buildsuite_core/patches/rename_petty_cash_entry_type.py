# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Rename the Journal Entry 'Entry Type' (voucher_type) from 'Petty Cash' to
	'Petty Cash Issue'. The Select option was renamed (property_field.py), so existing
	disbursement JEs would otherwise carry a value no longer in the option list — which
	also hides the Petty Cash Request link field (its depends_on now checks the new
	value). Straight column update; docstatus is untouched, so submitted entries are safe."""
	frappe.db.sql(
		"UPDATE `tabJournal Entry` SET voucher_type = 'Petty Cash Issue' WHERE voucher_type = 'Petty Cash'"
	)
	frappe.db.commit()  # nosemgrep
