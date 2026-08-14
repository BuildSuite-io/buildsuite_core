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
from frappe.utils import flt, formatdate, getdate, now_datetime

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
	by a User (requested_by); the holder is stamped on the GL via the `employee`
	Accounting Dimension (see install.seed_employee_accounting_dimension), so we resolve
	the User -> Employee link to keep issued float and later spend on one ledger."""
	if not user:
		return None
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def post_disbursement_journal_entry(doc):
	"""Build + submit the disbursement JE and return its name."""
	amount = flt(doc.amount)
	if amount <= 0:
		frappe.throw(_("Disbursement amount must be greater than zero."))

	petty = resolve_petty_cash_account(doc.company)
	# Imprest (custody) treatment: cash moves from the source into the holder's custody —
	# Dr Petty Cash (Asset/Cash) / Cr source. The Petty Cash balance is total cash out with
	# employees. The holder is stamped on the Petty Cash leg via the `employee` Accounting
	# Dimension (party isn't allowed on a Cash account) — ERPNext propagates it to GL Entry
	# natively, and the balance/transaction endpoints read GL Entry.employee. Holder is
	# mandatory (spec PF-02 rule 1).
	employee = employee_for_user(doc.requested_by)
	if not employee:
		frappe.throw(
			_("Only employees hold petty cash — no active Employee is linked to {0}.").format(
				doc.requested_by
			)
		)

	je = frappe.new_doc("Journal Entry")
	# Categorise as a Petty Cash Issue entry (Entry Type). This is the JE's own voucher_type
	# Select — NOT GL Entry.voucher_type (which stays the doctype name "Journal Entry"), so
	# the petty-cash reconciliation that filters GL on "Journal Entry" is unaffected.
	je.voucher_type = "Petty Cash Issue"
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
	# The request's disburse() drives the state change itself; tell the JE hooks to stand
	# down so they don't also flip the request (which would double-save it). The hooks are
	# for JEs posted by hand in Desk, which have no such orchestration.
	je.flags.ignore_petty_cash_sync = True
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
	je.flags.ignore_petty_cash_sync = True  # cancel_disbursement() reverts the request itself
	je.cancel()
	# Drop the JE→request back-link so a reversed direct issue (which is then deleted) isn't
	# blocked by the cancelled JE still referencing it.
	je.db_set("petty_cash_request", None)


# ---------------------------------------------------------------------------
# Direct Journal Entry disbursement (Desk, no Vue app)
# ---------------------------------------------------------------------------
# Bigger teams often post the disbursement Journal Entry straight in Desk instead of using
# the app. These hooks make that path behave like the app: link the JE to a Petty Cash
# Request (the `petty_cash_request` field), and on submit the request flips to Disbursed;
# on cancel it reverts. The holder is stamped on the Petty Cash leg so the GL / per-holder
# reconciliation still attributes the float.


def _je_funding_account(doc, company):
	"""The credited Bank/Cash source on a disbursement JE (Dr Petty Cash / Cr source)."""
	petty = get_petty_cash_account(company)
	for row in doc.get("accounts") or []:
		if flt(row.credit_in_account_currency) > 0 and row.account != petty:
			return row.account
	return None


def stamp_holder_on_petty_cash_je(doc, method=None):
	"""validate hook: a JE linked to a Petty Cash Request must carry the holder on its Petty
	Cash line, so the GL and the per-holder reconciliation attribute the float. Auto-fill it
	from the request's holder when a Desk user left it blank. Idempotent — the app's JE already
	has it set, so this is a no-op there."""
	request = doc.get("petty_cash_request")
	if not request:
		return

	company, requested_by = frappe.db.get_value(
		"Petty Cash Request", request, ["company", "requested_by"]
	) or (None, None)
	holder = employee_for_user(requested_by)
	if not holder:
		return

	petty = get_petty_cash_account(company) if company else None
	if not petty:
		return
	for row in doc.get("accounts") or []:
		if row.account == petty and not row.get("employee"):
			row.employee = holder


def sync_petty_cash_request_on_je_submit(doc, method=None):
	"""on_submit hook: submitting a JE linked to a Requested Petty Cash Request disburses it —
	the same end state as the app's disburse(), for JEs posted by hand in Desk."""
	if doc.flags.get("ignore_petty_cash_sync"):
		return
	request = doc.get("petty_cash_request")
	if not request:
		return

	status, company, linked = frappe.db.get_value(
		"Petty Cash Request", request, ["status", "company", "journal_entry"]
	)
	if status == "Disbursed":
		if linked and linked != doc.name:
			frappe.throw(_("Petty Cash Request {0} is already disbursed by {1}.").format(request, linked))
		return
	if status != "Requested":
		frappe.throw(
			_("Petty Cash Request {0} is {1} — only a Requested one can be disbursed.").format(
				request, status
			)
		)

	frappe.db.set_value(
		"Petty Cash Request",
		request,
		{
			"status": "Disbursed",
			"journal_entry": doc.name,
			"paid_from": _je_funding_account(doc, company),
			"disbursed_by": frappe.session.user,
			"disbursed_on": now_datetime(),
		},
	)
	frappe.get_doc("Petty Cash Request", request).add_comment(
		"Comment", _("Disbursed via Journal Entry {0}").format(doc.name)
	)


def revert_petty_cash_request_on_je_cancel(doc, method=None):
	"""on_cancel hook: cancelling a JE that disbursed a request reverts it to Requested."""
	if doc.flags.get("ignore_petty_cash_sync"):
		return
	request = doc.get("petty_cash_request")
	if not request:
		return
	if frappe.db.get_value("Petty Cash Request", request, "status") != "Disbursed":
		return

	frappe.db.set_value(
		"Petty Cash Request",
		request,
		{
			"status": "Requested",
			"journal_entry": None,
			"paid_from": None,
			"disbursed_by": None,
			"disbursed_on": None,
		},
	)
	frappe.get_doc("Petty Cash Request", request).add_comment(
		"Comment", _("Disbursement reversed — Journal Entry {0} cancelled").format(doc.name)
	)


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


def reconciled_holder_balances(company=None):
	"""Per-holder petty-cash position from the GL, reconciling the two legs into one
	view (the prototype's Balances tab): disbursed = float in (debits), spent = float
	out (credits), balance = net in hand. Keyed on the holder Employee, so it needs the
	disbursement / expense JEs to carry `employee` (they do).
	"""
	conditions = "a.account_name = %(petty)s AND gle.is_cancelled = 0 AND gle.employee IS NOT NULL AND gle.employee != ''"
	params = {"petty": PETTY_CASH_ACCOUNT_NAME}
	if company:
		conditions += " AND a.company = %(company)s"
		params["company"] = company

	rows = frappe.db.sql(
		f"""
		SELECT gle.employee AS employee,
			COALESCE(SUM(gle.debit), 0) AS disbursed,
			COALESCE(SUM(gle.credit), 0) AS spent
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` a ON a.name = gle.account
		WHERE {conditions}
		GROUP BY gle.employee
		""",
		params,
		as_dict=True,
	)

	name_map = {
		e.name: e.employee_name
		for e in (
			frappe.get_all(
				"Employee",
				filters={"name": ("in", [r.employee for r in rows])},
				fields=["name", "employee_name"],
			)
			if rows
			else []
		)
	}

	out = []
	for r in rows:
		disbursed = flt(r.disbursed)
		spent = flt(r.spent)
		out.append(
			{
				"employee": r.employee,
				"holder": name_map.get(r.employee) or r.employee,
				"disbursed": disbursed,
				"spent": spent,
				"balance": round(disbursed - spent, 2),
			}
		)
	out.sort(key=lambda x: x["balance"], reverse=True)
	return out


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

	return {e.name: references.get(e.voucher_no, (e.voucher_type, e.voucher_no)) for e in gl_entries}


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
def get_transaction_list(employee, transaction_type=None, project=None, from_date=None, to_date=None):
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
	if frappe.db.exists("Account", {"account_name": PETTY_CASH_ACCOUNT_NAME, "company": doc.name}):
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
