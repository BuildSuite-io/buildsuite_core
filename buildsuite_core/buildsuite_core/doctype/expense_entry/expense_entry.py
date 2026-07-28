# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


class ExpenseEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.expense_entry_table.expense_entry_table import (
			ExpenseEntryTable,
		)

		amended_from: DF.Link | None
		company: DF.Link | None
		cost_center: DF.Link | None
		date: DF.Date
		description: DF.SmallText | None
		employee: DF.Link | None
		employee_name: DF.Data | None
		expense_entry_table: DF.Table[ExpenseEntryTable]
		journal_entry: DF.Link | None
		naming_series: DF.Literal["EE-.YY.-"]
		paid_from: DF.Literal["Petty Cash", "Company"]
		payment_account: DF.Link
		payment_account_name: DF.Data | None
		project: DF.Link
		total_amount: DF.Currency
	# end: auto-generated types

	def validate(self):
		if not self.expense_entry_table:
			frappe.throw(_("At least one expense row is required."))

		# PF-04: holder is mandatory when paid from Petty Cash (drives the per-holder
		# balance); a Company-paid expense has no holder.
		if self.paid_from == "Petty Cash" and not self.employee:
			frappe.throw(_("Holder (Employee) is required when Paid From is Petty Cash."))
		if self.paid_from == "Company":
			self.employee = None

		self.total_amount = sum(flt(row.amount) for row in self.expense_entry_table)

		for idx, row in enumerate(self.expense_entry_table, start=1):
			if flt(row.amount) <= 0:
				frappe.throw(_("Row #{0}: Amount must be greater than zero.").format(idx))
			if not row.expense_account or not row.payment_account:
				frappe.throw(
					_("Row #{0}: Both Expense Account and Payment Account are required.").format(idx)
				)

		self.validate_single_company()
		self.set_description()

	def validate_single_company(self):
		"""Every account + the holder must belong to this entry's company, else the Journal
		Entry is rejected (ERPNext surfaces it as a cryptic multi-currency error). Multi-company
		is a later version; today all finance posts to one company. The company itself is the
		project's (see accounting-company-anchored-to-project) — the seam stays, this only
		enforces consistency within whatever that company is."""
		for idx, row in enumerate(self.expense_entry_table, start=1):
			for account in (row.expense_account, row.payment_account):
				if account and frappe.db.get_value("Account", account, "company") != self.company:
					frappe.throw(
						_("Row #{0}: Account {1} does not belong to company {2}.").format(
							idx, frappe.bold(account), frappe.bold(self.company)
						)
					)

		if self.employee and frappe.db.get_value("Employee", self.employee, "company") != self.company:
			frappe.throw(
				_("Holder {0} does not belong to company {1}.").format(
					frappe.bold(self.employee), frappe.bold(self.company)
				)
			)

	def on_submit(self):
		self.create_journal_entry()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
		self.cancel_journal_entry()

	# ------------------------------------------------------------------
	# Journal Entry
	# ------------------------------------------------------------------

	def create_journal_entry(self):
		accounting_dimensions = get_accounting_dimensions() or []
		default_cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		# PF-04: the holder rides on the CREDIT (Petty Cash) leg only, and only when paid
		# from petty cash. The expense debit carries project/cost dimensions, not the holder;
		# a Company-paid credit (Bank/Cash) has no holder.
		holder = self.employee if self.paid_from == "Petty Cash" else None

		accounts = []
		for row in self.expense_entry_table:
			cost_center = row.cost_center or self.cost_center or default_cost_center

			# Debit: expense account (project cost — no holder)
			accounts.append(
				self.get_account_row(row, row.expense_account, flt(row.amount), 0, cost_center, accounting_dimensions, employee=None)
			)
			# Credit: payment account — Petty Cash (holder stamped) or the company's Bank/Cash
			accounts.append(
				self.get_account_row(row, row.payment_account, 0, flt(row.amount), cost_center, accounting_dimensions, employee=holder)
			)

		if not accounts:
			return

		je = frappe.new_doc("Journal Entry")
		je.update(
			{
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": self.date,
				"multi_currency": 0,
				"remark": self.description,
				"user_remark": self.description,
				"reference_doctype": self.doctype,
				"reference_docname": self.name,
			}
		)
		je.set("accounts", accounts)
		je.flags.ignore_permissions = True
		je.insert()
		je.submit()

		self.db_set("journal_entry", je.name)

	def cancel_journal_entry(self):
		if not self.journal_entry:
			return

		docstatus = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
		if docstatus == 1:
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			je.flags.ignore_permissions = True
			je.cancel()

		self.db_set("journal_entry", None)

	def get_account_row(self, row, account, debit, credit, cost_center, accounting_dimensions, employee=None):
		entry = {
			"account": account,
			"debit_in_account_currency": debit or 0,
			"credit_in_account_currency": credit or 0,
			"cost_center": cost_center,
			"project": row.project or self.project,
			"user_remark": row.description,
		}
		# The holder is set explicitly (PF-04: Petty Cash credit leg only), so don't let the
		# generic dimension loop re-stamp `employee` onto the expense debit.
		if employee:
			entry["employee"] = employee

		for dimension in accounting_dimensions:
			if dimension == "employee":
				continue
			value = row.get(dimension) or self.get(dimension)
			if value:
				entry[dimension] = value

		return entry

	# ------------------------------------------------------------------
	# Description
	# ------------------------------------------------------------------

	def set_description(self):
		before_save = self.get_doc_before_save()
		old_description = before_save.description if before_save else None

		if self.description and self.description != old_description:
			full_name = frappe.db.get_value("User", frappe.session.user, "full_name")
			self.description = f"{self.description} - Updated by {full_name}"
		elif old_description and "Updated by" in old_description:
			self.description = old_description
		else:
			self.description = self.build_description()

	def build_description(self):
		employee_name = (
			frappe.db.get_value("Employee", self.employee, "employee_name") if self.employee else ""
		)
		project_name = frappe.db.get_value("Project", self.project, "project_name") if self.project else ""
		payment_account = self.payment_account or "N/A"

		expenses = ", ".join(row.expense_account for row in self.expense_entry_table if row.expense_account)

		parts = [f"Amount of {flt(self.total_amount)} for"]
		if expenses:
			parts.append(f"Expenses include - {expenses}.")
		if project_name:
			parts.append(f"For Project: {project_name} in")

		if "Petty Cash" in payment_account:
			parts.append(f"{payment_account} of {employee_name}.")
		else:
			parts.append(f"{payment_account}.")

		return " ".join(parts)


# ----------------------------------------------------------------------
# Link queries
# ----------------------------------------------------------------------


def get_petty_cash_account(company, throw=True):
	account = frappe.db.get_value(
		"Account", {"account_name": "Petty Cash", "company": company, "is_group": 0}, "name"
	)
	if not account and throw:
		frappe.throw(
			_("Petty Cash account not found for company {0}. Contact Accounts Manager.").format(company)
		)
	return account


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_petty_cash_account_query(doctype, txt, searchfield, start, page_len, filters):
	"""Return only the petty cash account for the given company."""
	company = (filters or {}).get("company")
	if not company:
		return []

	account = get_petty_cash_account(company, throw=False)
	if not account:
		return []

	return frappe.db.sql(
		"""
		SELECT name, account_name
		FROM `tabAccount`
		WHERE name = %(account)s
		  AND (name LIKE %(txt)s OR account_name LIKE %(txt)s)
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"account": account,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_employee_for_petty_cash_user(doctype, txt, searchfield, start, page_len, filters):
	"""Return only the employee record linked to the logged-in Petty Cash user."""
	user = (filters or {}).get("user")
	if not user:
		return []

	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return []

	return frappe.db.sql(
		"""
		SELECT name, employee_name
		FROM `tabEmployee`
		WHERE name = %(employee)s
		  AND (name LIKE %(txt)s OR employee_name LIKE %(txt)s)
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"employee": employee,
			"txt": f"%{txt}%",
			"start": start,
			"page_len": page_len,
		},
	)