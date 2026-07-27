# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Petty Cash Request → Journal Entry.

Disbursing a petty cash request moves money out of a bank/cash account into the company's
Petty Cash account via a submitted Journal Entry (Dr Petty Cash / Cr paid-from), carrying the
project accounting dimension. Cancelling the disbursement cancels the JE.

Also exposes the balance / transaction-list endpoints used by the petty cash portal.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

PETTY_CASH_ACCOUNT_NAME = "Petty Cash"
PETTY_CASH_PARENT_ACCOUNT = "Cash In Hand"


# ---------------------------------------------------------------------------
# Account resolution
# ---------------------------------------------------------------------------


def get_petty_cash_account(company):
	"""Read-only lookup of the company's Petty Cash ledger. Returns None if absent.

	Prefer this in reporting paths — `resolve_petty_cash_account` creates the account as a
	side effect, which a GET-style endpoint should never do.
	"""
	if not company:
		return None

	default = frappe.db.get_single_value("BuildSuite Core Settings", "default_petty_cash_account")
	if default and frappe.db.get_value("Account", default, "company") == company:
		return default

	return frappe.db.get_value(
		"Account",
		{"account_name": PETTY_CASH_ACCOUNT_NAME, "company": company, "is_group": 0},
		"name",
	)


def resolve_petty_cash_account(company):
	"""As above, but creates a per-company 'Petty Cash' asset account when missing."""
	account = get_petty_cash_account(company)
	if account:
		return account

	from buildsuite_core.utils.subcontract_billing import _ensure_account

	return _ensure_account(company, PETTY_CASH_ACCOUNT_NAME, "Asset", "Cash", "Current Assets")


# ---------------------------------------------------------------------------
# Journal Entry posting
# ---------------------------------------------------------------------------


def employee_for_user(user):
	"""The active Employee linked to a User, or None. Petty Cash Requests are raised
	by a User (requested_by); the employee ledger (GL Entry.employee) keys on Employee,
	so we resolve the link to keep issued float and later spend on one ledger."""
	if not user:
		return None
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def post_disbursement_journal_entry(doc):
	"""Build + submit the disbursement JE and return its name."""
	amount = flt(doc.amount)
	if amount <= 0:
		frappe.throw(_("Disbursement amount must be greater than zero."))

	petty = resolve_petty_cash_account(doc.company)
	# Tag the holder on the Petty Cash (debit) line so the issued float lands in the
	# same employee ledger the balance / transaction endpoints read.
	employee = employee_for_user(doc.requested_by)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = doc.company
	je.posting_date = str(doc.request_date) if doc.request_date else None
	je.user_remark = f"Petty cash {doc.name}: {doc.purpose or ''}"[:140]
	if frappe.get_meta("Journal Entry").has_field("petty_cash_request"):
		je.petty_cash_request = doc.name

	je.append(
		"accounts",
		{"account": petty, "debit_in_account_currency": amount, "project": doc.project, "employee": employee},
	)
	je.append(
		"accounts",
		{"account": doc.paid_from, "credit_in_account_currency": amount, "project": doc.project},
	)

	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def cancel_disbursement_journal_entry(doc):
	if not doc.journal_entry:
		return

	docstatus = frappe.db.get_value("Journal Entry", doc.journal_entry, "docstatus")
	if docstatus != 1:
		return

	je = frappe.get_doc("Journal Entry", doc.journal_entry)
	je.flags.ignore_permissions = True
	je.cancel()


# ---------------------------------------------------------------------------
# Shared helpers for the balance endpoints
# ---------------------------------------------------------------------------


def _employee_context(employee):
	"""Validate access and return (company, petty_cash_account) for an employee."""
	if not employee:
		frappe.throw(_("Employee is required."))

	company = frappe.db.get_value("Employee", employee, "company")
	if not company:
		frappe.throw(_("Employee {0} not found.").format(employee))

	# These endpoints are whitelisted: without this, any logged-in user can read any
	# employee's petty cash position by guessing an ID.
	if not frappe.has_permission("Employee", doc=employee):
		raise frappe.PermissionError

	account = get_petty_cash_account(company)
	if not account:
		frappe.throw(_("Petty Cash account not found for {0}.").format(company))

	return company, account


def _posted_balance(employee, account):
	"""Net Dr − Cr of submitted, non-cancelled GL entries."""
	balance = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0)
		FROM `tabGL Entry`
		WHERE is_cancelled = 0
			AND employee = %(employee)s
			AND account = %(account)s
		""",
		{"employee": employee, "account": account},
	)
	return flt(balance[0][0]) if balance else 0.0


def _draft_journal_balance(employee, account):
	"""Net Dr − Cr sitting in unsubmitted Journal Entries."""
	balance = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(jea.debit), 0) - COALESCE(SUM(jea.credit), 0)
		FROM `tabJournal Entry Account` jea
		INNER JOIN `tabJournal Entry` je ON je.name = jea.parent
		WHERE jea.employee = %(employee)s
			AND jea.account = %(account)s
			AND je.docstatus = 0
		""",
		{"employee": employee, "account": account},
	)
	return flt(balance[0][0]) if balance else 0.0


def _pending_expense_total(employee, account):
	"""Total of expense lines awaiting approval against the petty cash account."""
	total = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(eet.amount), 0)
		FROM `tabExpense Entry Table` eet
		INNER JOIN `tabExpense Entry` et ON et.name = eet.parent
		WHERE eet.employee = %(employee)s
			AND eet.payment_account = %(account)s
			AND et.docstatus = 0
		""",
		{"employee": employee, "account": account},
	)
	return flt(total[0][0]) if total else 0.0


# ---------------------------------------------------------------------------
# Whitelisted balance endpoints
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_balance_amount_approved(employee):
	"""Settled balance — submitted GL entries only."""
	_company, account = _employee_context(employee)
	return _posted_balance(employee, account)


@frappe.whitelist()
def get_pending_approval_balance(employee):
	"""Expense claims raised but not yet approved."""
	_company, account = _employee_context(employee)
	return _pending_expense_total(employee, account)


@frappe.whitelist()
def get_total_balance_include_review(employee):
	"""Settled balance adjusted for drafts still under review."""
	_company, account = _employee_context(employee)
	return (
		_posted_balance(employee, account)
		+ _draft_journal_balance(employee, account)
		- _pending_expense_total(employee, account)
	)


# Backwards-compatible alias for the original misspelled endpoint. Remove once the
# JS/portal callers have been repointed.
@frappe.whitelist()
def get_total_balance_inculde_review(employee):
	return get_total_balance_include_review(employee)


# ---------------------------------------------------------------------------
# Transaction list
# ---------------------------------------------------------------------------


def _resolve_voucher_targets(gl_entries):
	"""Map each GL row to the document the UI should link to.

	Journal Entries point at their reference document when one is set; everything else
	links to itself. Returns {gl_entry_name: (doctype, docname)}.
	"""
	je_names = {e.voucher_no for e in gl_entries if e.voucher_type == "Journal Entry"}
	references = {}

	if je_names:
		meta = frappe.get_meta("Journal Entry")
		if meta.has_field("reference_doctype") and meta.has_field("reference_docname"):
			for row in frappe.get_all(
				"Journal Entry",
				filters={"name": ("in", list(je_names))},
				fields=["name", "reference_doctype", "reference_docname"],
			):
				if row.reference_doctype and row.reference_docname:
					references[row.name] = (row.reference_doctype, row.reference_docname)

	return {
		e.name: references.get(e.voucher_no, (e.voucher_type, e.voucher_no)) for e in gl_entries
	}


def _fetch_display_fields(targets):
	"""Batch-load title/remark for a set of (doctype, docname) pairs."""
	by_doctype = defaultdict(set)
	for doctype, docname in targets:
		by_doctype[doctype].add(docname)

	display = {}
	for doctype, names in by_doctype.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		meta = frappe.get_meta(doctype)
		fields = ["name"] + [f for f in ("title", "remarks", "remark") if meta.has_field(f)]

		for row in frappe.get_all(doctype, filters={"name": ("in", list(names))}, fields=fields):
			display[(doctype, row.name)] = {
				"title": row.get("title") or row.name,
				"remark": row.get("remarks") or row.get("remark") or "",
			}

	return display


@frappe.whitelist()
def get_transaction_list(
	employee, transaction_type=None, project=None, from_date=None, to_date=None
):
	"""Petty cash ledger for an employee, newest first, with a running balance.

	The running balance is accumulated across the employee's full history before the
	display filters are applied, so a filtered view still shows true account balances.
	"""
	_company, petty_cash = _employee_context(employee)

	# Normalise the "None" strings the portal sends for cleared filters.
	transaction_type = transaction_type if transaction_type not in (None, "None", "") else None
	project = project if project not in (None, "None", "") else None
	from_date = getdate(from_date) if from_date not in (None, "None", "") else None
	to_date = getdate(to_date) if to_date not in (None, "None", "") else None

	filters = {"is_cancelled": 0, "employee": employee, "account": petty_cash}
	if project:
		filters["project"] = project

	gl_entries = frappe.get_all(
		"GL Entry",
		filters=filters,
		fields=[
			"name",
			"voucher_type",
			"voucher_no",
			"credit",
			"debit",
			"project",
			"posting_date",
			"creation",
		],
		order_by="posting_date asc, creation asc",
	)
	if not gl_entries:
		return []

	# Everything the rows need, resolved in a handful of queries rather than per row.
	voucher_targets = _resolve_voucher_targets(gl_entries)
	display = _fetch_display_fields(set(voucher_targets.values()))

	project_names = {e.project for e in gl_entries if e.project}
	project_titles = (
		{
			p.name: p.project_name
			for p in frappe.get_all(
				"Project", filters={"name": ("in", list(project_names))}, fields=["name", "project_name"]
			)
		}
		if project_names
		else {}
	)

	rows = []
	balance = 0.0

	for idx, entry in enumerate(gl_entries):
		balance += flt(entry.debit) - flt(entry.credit)

		if transaction_type == "Received" and not flt(entry.debit):
			continue
		if transaction_type == "Paid" and not flt(entry.credit):
			continue
		if from_date and to_date and not (from_date <= entry.posting_date <= to_date):
			continue

		doctype, docname = voucher_targets[entry.name]
		info = display.get((doctype, docname), {})

		rows.append(
			{
				"idx": idx,
				"name": entry.name,
				"doctype": doctype.lower().replace(" ", "-"),
				"remark": info.get("remark", ""),
				"creation": entry.creation,
				"id": docname,
				"paid": flt(entry.credit),
				"received": flt(entry.debit),
				"project": project_titles.get(entry.project),
				"posting_date": formatdate(entry.posting_date, "dd-mm-yyyy"),
				"title": info.get("title", docname),
				"balance": balance,
			}
		)

	rows.reverse()
	return rows


# ---------------------------------------------------------------------------
# Company setup hook
# ---------------------------------------------------------------------------


def create_account(doc, method=None):
	"""on_update hook for Company — ensure the Petty Cash ledger exists.

	Not whitelisted: this is a document event, and exposing it would let any user
	trigger account creation.
	"""
	if frappe.db.exists(
		"Account", {"account_name": PETTY_CASH_ACCOUNT_NAME, "company": doc.name}
	):
		return

	parent = frappe.db.get_value(
		"Account", {"account_name": PETTY_CASH_PARENT_ACCOUNT, "company": doc.name}, "name"
	)
	if not parent:
		frappe.log_error(
			f"Cannot create Petty Cash account for {doc.name}: "
			f"parent account '{PETTY_CASH_PARENT_ACCOUNT}' not found.",
			"Petty Cash setup",
		)
		return

	account = frappe.new_doc("Account")
	account.update(
		{
			"account_name": PETTY_CASH_ACCOUNT_NAME,
			"root_type": "Asset",
			"account_type": "Cash",
			"company": doc.name,
			"parent_account": parent,
		}
	)
	account.insert(ignore_permissions=True)