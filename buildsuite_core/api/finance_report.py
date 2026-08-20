# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Real-data backends for the two bespoke Project Finance report views (Receivables & Payables
aged, Financial Position). These mirror what the prototype's mock store returned, so the Vue
views render the prototype layout against live data. Finance is single-company for now, so both
default to the site's default company."""

import frappe
from frappe.utils import flt

from buildsuite_core.utils.project import default_company

BUCKETS = ["Current", "0-30", "31-60", "61-90", "90+"]


def _bucket(days):
	days = int(days or 0)
	if days <= 0:
		return "Current"
	if days <= 30:
		return "0-30"
	if days <= 60:
		return "31-60"
	if days <= 90:
		return "61-90"
	return "90+"


@frappe.whitelist()
def receivables_and_payables(company=None):
	"""Aged open receivables (Sales Invoices) and payables (Purchase Invoices), each row bucketed
	by days overdue. Payables carry a supplier/subcontractor kind + any retention withheld."""
	company = company or default_company()
	receivables = frappe.db.sql(
		"""SELECT name AS id, customer_name AS party, due_date AS due,
			outstanding_amount AS outstanding, GREATEST(DATEDIFF(CURDATE(), due_date), 0) AS days_overdue
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND outstanding_amount > 0 AND company = %s
		ORDER BY due_date""",
		(company,),
		as_dict=True,
	)
	payables = frappe.db.sql(
		"""SELECT pi.name AS id, pi.supplier_name AS party, pi.due_date AS due,
			pi.outstanding_amount AS outstanding, GREATEST(DATEDIFF(CURDATE(), pi.due_date), 0) AS days_overdue,
			IFNULL((SELECT SUM(sb.retention_amount) FROM `tabSubcontractor Bill` sb
				WHERE sb.purchase_invoice = pi.name AND sb.docstatus = 1), 0) AS retention,
			(SELECT s.supplier_group FROM `tabSupplier` s WHERE s.name = pi.supplier) AS supplier_group
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1 AND pi.outstanding_amount > 0 AND pi.company = %s
		ORDER BY pi.due_date""",
		(company,),
		as_dict=True,
	)
	for r in receivables:
		r["bucket"] = _bucket(r["days_overdue"])
		r["due"] = str(r["due"]) if r.get("due") else None
	for r in payables:
		r["bucket"] = _bucket(r["days_overdue"])
		r["due"] = str(r["due"]) if r.get("due") else None
		r["kind"] = "subcontractor" if (r.get("supplier_group") == "Subcontractor") else "supplier"
		r.pop("supplier_group", None)
	return {"receivables": receivables, "payables": payables, "buckets": BUCKETS}


def _account_names(company, account_type, contains=None, excludes=None):
	names = frappe.get_all(
		"Account", filters={"company": company, "account_type": account_type, "is_group": 0}, pluck="name"
	)
	if contains:
		names = [n for n in names if contains in n]
	if excludes:
		names = [n for n in names if not any(x in n for x in excludes)]
	return names


def _gl_balance(company, accounts):
	if not accounts:
		return 0.0
	return flt(
		frappe.db.sql(
			"""SELECT IFNULL(SUM(debit - credit), 0) FROM `tabGL Entry`
			WHERE is_cancelled = 0 AND company = %s AND account IN %s""",
			(company, tuple(accounts)),
		)[0][0]
	)


def _petty_split(company):
	"""Petty cash split by holder (the `employee` GL dimension): holders in credit hold cash
	(an asset — "petty cash with holders"), holders who overspent their float are owed the
	excess (a liability — "to reimburse"). Falls back to the net account balance if the holder
	dimension isn't present."""
	accounts = _account_names(company, "Cash", contains="Petty")
	if not accounts:
		return 0.0, 0.0
	if not frappe.db.has_column("GL Entry", "employee"):
		bal = _gl_balance(company, accounts)
		return (bal if bal > 0 else 0.0), (-bal if bal < 0 else 0.0)
	rows = frappe.db.sql(
		"""SELECT IFNULL(SUM(debit - credit), 0) AS bal FROM `tabGL Entry`
		WHERE is_cancelled = 0 AND company = %s AND account IN %s GROUP BY employee""",
		(company, tuple(accounts)),
		as_dict=True,
	)
	held = flt(sum(r.bal for r in rows if r.bal > 0))
	reimburse = flt(sum(-r.bal for r in rows if r.bal < 0))
	return held, reimburse


@frappe.whitelist()
def financial_position(company=None):
	"""What we have (bank, cash, petty cash out with holders, customers owe) vs what we owe
	(suppliers, subcontractors, retention held), and the net. Balances from the GL and open
	documents. Supplier/customer advances and own-pocket reimbursements aren't broken out yet."""
	company = company or default_company()

	def doc_sum(doctype, field):
		return flt(
			frappe.db.sql(
				f"SELECT IFNULL(SUM(`{field}`), 0) FROM `tab{doctype}` WHERE docstatus = 1 AND company = %s",
				(company,),
			)[0][0]
		)

	bank = _gl_balance(company, _account_names(company, "Bank"))
	cash = _gl_balance(company, _account_names(company, "Cash", excludes=["Petty"]))
	petty_out, to_reimburse = _petty_split(company)
	customers_owe = doc_sum("Sales Invoice", "outstanding_amount")
	retention = doc_sum("Subcontractor Bill", "retention_amount")

	# Advances = the still-unallocated portion of a party's advance Payment Entries: money we
	# paid suppliers ahead (an asset) / customers paid us ahead (a liability), not yet drawn
	# down against an invoice.
	advances_paid = flt(
		frappe.db.sql(
			"""SELECT IFNULL(SUM(unallocated_amount), 0) FROM `tabPayment Entry`
			WHERE docstatus = 1 AND payment_type = 'Pay' AND party_type = 'Supplier' AND company = %s""",
			(company,),
		)[0][0]
	)
	advances_received = flt(
		frappe.db.sql(
			"""SELECT IFNULL(SUM(unallocated_amount), 0) FROM `tabPayment Entry`
			WHERE docstatus = 1 AND payment_type = 'Receive' AND party_type = 'Customer' AND company = %s""",
			(company,),
		)[0][0]
	)

	# Split open payables into supplier vs subcontractor by the supplier's group.
	pay_rows = frappe.db.sql(
		"""SELECT pi.outstanding_amount AS amt,
			(SELECT s.supplier_group FROM `tabSupplier` s WHERE s.name = pi.supplier) AS grp
		FROM `tabPurchase Invoice` pi
		WHERE pi.docstatus = 1 AND pi.company = %s AND pi.outstanding_amount > 0""",
		(company,),
		as_dict=True,
	)
	subcontractors = flt(sum(r.amt for r in pay_rows if r.grp == "Subcontractor"))
	suppliers = flt(sum(r.amt for r in pay_rows if r.grp != "Subcontractor"))

	have = {
		"bank": bank,
		"cash": cash,
		"pettyCashOut": petty_out,
		"customersOwe": customers_owe,
		"advancesPaid": advances_paid,
	}
	owe = {
		"suppliers": suppliers,
		"subcontractors": subcontractors,
		"retention": retention,
		"advancesReceived": advances_received,
		"toReimburse": to_reimburse,
	}
	return {"have": have, "owe": owe, "net": sum(have.values()) - sum(owe.values())}


def _cash_bank_accounts(company):
	"""Bank + Cash accounts a statement can be drawn for, excluding Petty Cash (that's its own
	imprest report). Ordered Bank first, then by name."""
	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		fields=["name", "account_name", "account_type"],
		order_by="account_type, account_name",
	)
	return [a for a in accounts if "Petty" not in a.name]


@frappe.whitelist()
def cash_bank_accounts(company=None):
	"""The Bank/Cash accounts the Cash & Bank statement picker offers (single-company seam)."""
	company = company or default_company()
	return _cash_bank_accounts(company)


@frappe.whitelist()
def cash_bank_statement(account=None, from_date=None, to_date=None, company=None):
	"""A running-balance statement for one Bank/Cash account, from its GL. Cash/Bank are asset
	accounts, so a debit is money in and a credit is money out. The opening balance folds in
	everything posted before `from_date` (0 when no period is set — the statement runs from the
	beginning of the ledger), so the running balance is always correct even when rows are
	clipped to a period."""
	company = company or default_company()
	if not account:
		accts = _cash_bank_accounts(company)
		account = accts[0]["name"] if accts else None
	if not account:
		return {"account": None, "opening": 0, "movements": [], "totalIn": 0, "totalOut": 0, "closing": 0}

	acc = frappe.db.get_value("Account", account, ["name", "account_name", "account_type"], as_dict=True)

	opening = 0.0
	if from_date:
		opening = flt(
			frappe.db.sql(
				"""SELECT IFNULL(SUM(debit - credit), 0) FROM `tabGL Entry`
				WHERE is_cancelled = 0 AND company = %s AND account = %s AND posting_date < %s""",
				(company, account, from_date),
			)[0][0]
		)

	conds = "is_cancelled = 0 AND company = %s AND account = %s"
	params = [company, account]
	if from_date:
		conds += " AND posting_date >= %s"
		params.append(from_date)
	if to_date:
		conds += " AND posting_date <= %s"
		params.append(to_date)
	rows = frappe.db.sql(
		f"""SELECT posting_date, voucher_type, voucher_no, against, debit, credit, party_type, party, remarks
		FROM `tabGL Entry` WHERE {conds}
		ORDER BY posting_date, creation""",
		params,
		as_dict=True,
	)

	movements = []
	bal = opening
	total_in = total_out = 0.0
	for r in rows:
		money_in = flt(r.debit)
		money_out = flt(r.credit)
		bal += money_in - money_out
		total_in += money_in
		total_out += money_out
		who = r.party or r.against
		movements.append(
			{
				"date": str(r.posting_date),
				"label": f"{r.voucher_type} · {who}" if who else r.voucher_type,
				"ref": r.voucher_no,
				"voucher_type": r.voucher_type,
				"in": money_in,
				"out": money_out,
				"balance": flt(bal),
			}
		)

	return {
		"account": acc,
		"opening": flt(opening),
		"movements": movements,
		"totalIn": flt(total_in),
		"totalOut": flt(total_out),
		"closing": flt(bal),
	}
