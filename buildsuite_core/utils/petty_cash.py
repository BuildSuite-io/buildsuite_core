# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Petty Cash Request → Journal Entry.

Disbursing a petty cash request moves money out of a bank/cash account into the company's
Petty Cash account via a submitted Journal Entry (Dr Petty Cash / Cr paid-from), carrying the
project accounting dimension. Cancelling the disbursement cancels the JE."""

import frappe
from frappe import _
from frappe.utils import flt

PETTY_CASH_ACCOUNT_NAME = "Petty Cash"


def resolve_petty_cash_account(company):
	"""The company's Petty Cash ledger — the BuildSuite Core Settings default (if it belongs to
	the company), else a per-company 'Petty Cash' asset account, created if absent."""
	default = frappe.db.get_single_value("BuildSuite Core Settings", "default_petty_cash_account")
	if default and frappe.db.get_value("Account", default, "company") == company:
		return default
	from buildsuite_core.utils.subcontract_billing import _ensure_account

	return _ensure_account(company, PETTY_CASH_ACCOUNT_NAME, "Asset", "Cash", "Current Assets")


def post_disbursement_journal_entry(doc):
	"""Build + submit the disbursement JE and return its name."""
	petty = resolve_petty_cash_account(doc.company)
	amount = flt(doc.amount)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = doc.company
	je.posting_date = str(doc.request_date) if doc.request_date else None
	je.user_remark = (f"Petty cash {doc.name}: {doc.purpose or ''}")[:140]
	if frappe.get_meta("Journal Entry").has_field("petty_cash_request"):
		je.petty_cash_request = doc.name
	je.append("accounts", {"account": petty, "debit_in_account_currency": amount, "project": doc.project})
	je.append(
		"accounts", {"account": doc.paid_from, "credit_in_account_currency": amount, "project": doc.project}
	)
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def cancel_disbursement_journal_entry(doc):
	if not doc.journal_entry or not frappe.db.exists("Journal Entry", doc.journal_entry):
		return
	je = frappe.get_doc("Journal Entry", doc.journal_entry)
	if je.docstatus == 1:
		je.flags.ignore_permissions = True
		je.cancel()
