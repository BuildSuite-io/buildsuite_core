# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Keep the Payment Entry Reference No optional across BuildSuite (SPA + mobile).

ERPNext makes Reference No + Reference Date mandatory for a Bank Mode of Payment. BuildSuite
treats them as optional, so this before_validate hook defaults them when a bank payment/advance
is saved without one — covering every Payment Entry path (advances, receipts, bill payments) in
one place, instead of per-endpoint patches.
"""

import frappe
from frappe.utils import nowdate


def default_bank_reference(doc, method=None):
	if doc.reference_no and doc.reference_date:
		return
	# Mirror ERPNext's PaymentEntry.validate_transaction_reference: the check keys off the
	# BANK ACCOUNT's account_type (paid_to for Receive, paid_from for Pay), not the mode of
	# payment. Default the reference only when that account is a Bank account.
	bank_account = doc.paid_to if doc.payment_type == "Receive" else doc.paid_from
	if not bank_account:
		return
	if frappe.get_cached_value("Account", bank_account, "account_type") != "Bank":
		return
	if not doc.reference_no:
		doc.reference_no = doc.name or "Payment"
	if not doc.reference_date:
		doc.reference_date = doc.posting_date or nowdate()
