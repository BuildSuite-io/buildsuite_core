# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)

from frappe.utils import cstr, flt, get_link_to_form

class ExpenseEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.expense_entry_table.expense_entry_table import ExpenseEntryTable
		from frappe.types import DF

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
		payment_account: DF.Link
		payment_account_name: DF.Data | None
		project: DF.Link
		total_amount: DF.Currency
	# end: auto-generated types

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.expense_entry_table.expense_entry_table import ExpenseEntryTable
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link | None
		cost_center: DF.Link | None
		date: DF.Date
		description: DF.SmallText | None
		employee: DF.Link | None
		employee_name: DF.Data | None
		expense_entry_table: DF.Table[ExpenseEntryTable]
		naming_series: DF.Data
		payment_account: DF.Link
		payment_account_name: DF.Data | None
		project: DF.Link
		total_amount: DF.Currency

	def validate(self):
		amount = 0
		for expense_entry in self.expense_entry_table:
			amount += expense_entry.amount
		self.db_set('total_amount', amount)
		generate_remarks(self)
    
	def on_submit(self):
		if self.expense_entry_table:
			accounts = []
			for expense_entry in self.expense_entry_table:
				accounting_dimensions = get_accounting_dimensions() or []
				if expense_entry.payment_account:
					accounts.append(create_account_entry(
						expense_entry.payment_account,
						None,
						expense_entry.amount,
						expense_entry.cost_center or frappe.db.get_value("Company", self.company, 'cost_center'),
						expense_entry.project,
						expense_entry.employee,
						expense_entry.description,
						accounting_dimensions
					))
				if expense_entry.expense_account:
					accounts.append(create_account_entry(
						expense_entry.expense_account,
						expense_entry.amount,
						None,
						expense_entry.cost_center or frappe.db.get_value("Company", self.company, 'cost_center'),
						expense_entry.project,
						expense_entry.employee,
						expense_entry.description,
						accounting_dimensions
					))
				journal_entry = create_journal_entry_doc(accounts, self.company, self.date, 0, "Journal Entry", self.description, self.doctype, self.name)
				self.db_set('journal_entry', journal_entry.name)
				self.reload()

	def on_cancel(self):
		if self.journal_entry:
			journal_entry_doc = frappe.get_doc("Journal Entry", self.journal_entry)
			journal_entry_doc.cancel()
			self.db_set('journal_entry', None)
			self.reload()
	pass

def create_journal_entry_doc(accounts, company, posting_date, multi_currency, voucher_type, remark, reference_doctype, reference_docname):
	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.voucher_type = voucher_type
	journal_entry.company = company
	journal_entry.posting_date = posting_date
	journal_entry.multi_currency = multi_currency
	journal_entry.docstatus = 1
	journal_entry.remark = remark
	journal_entry.reference_doctype = reference_doctype
	journal_entry.reference_docname = reference_docname
	journal_entry.set("accounts", accounts)
	journal_entry.save(ignore_permissions=True)
	return journal_entry

def create_account_entry(account, debit_amount, cerdit_amount, cost_center, project, employee, user_remark, accounting_dimensions):
    precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
    entry = {
        "account": account,
        "debit_in_account_currency": flt(debit_amount, precision) if debit_amount else None,
        "credit_in_account_currency": flt(cerdit_amount, precision) if cerdit_amount else None,
        "cost_center": cost_center,
        "project": project,
		"user_remark":user_remark,
		"employee":employee
    }
    return update_accounting_dimensions(entry, accounting_dimensions)


def update_accounting_dimensions(row, accounting_dimensions):
    for dimension in accounting_dimensions:
        row.update({dimension: row.get(dimension)})
    return row

def generate_remarks(self):
    full_name = frappe.db.get_value("User", frappe.session.user, 'full_name')
    old_remark = self.get_doc_before_save().description if self.get_doc_before_save() else None
    
    if self.description != old_remark:
        if not self.description:  # If remark is empty
            self.description = remarks_creation(self)
        else:
            self.description = f"{self.remark} - Updated by {full_name}"
    elif old_remark and "Updated by" in old_remark:
        self.description = old_remark
    else:
        # If none of the above, generate the remark
        self.description = remarks_creation(self)

def remarks_creation(self):
    employee = frappe.db.get_value("Employee", self.employee, 'employee_name') or ""
    project = frappe.db.get_value("Project", self.project, 'project_name') or ""
    mode_of_payment_account = self.payment_account or "N/A"
    amount = self.total_amount or "N/A"
    expense_entry_table = self.expense_entry_table or []
    remarks = ''

    # Start constructing the remarks
    remarks += f"Amount of {amount} for "

    expense_details = [single_expense.expense_account for single_expense in expense_entry_table]
    expense_summary = ", ".join(expense_details)
    remarks += f"Expenses include - {expense_summary}."
    
    # Add project if available
    if project:
        remarks += f" For Project: {project} in "
    
    if "Petty Cash" in mode_of_payment_account:
        remarks += f"{mode_of_payment_account} of {employee}."
    else:
        remarks += f" {mode_of_payment_account}."
    
    return remarks

@frappe.whitelist()
def get_petty_cash_account_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Return only the petty cash account for the given company.
    Used by set_query for field 'mode_of_payment_account'
    """
    company = filters.get("company")
    if not company:
        return []

    # Get configured petty cash account for the company
    petty_cash_account = get_petty_cash_account(company)
    if not petty_cash_account:
        return []

    # Support partial search matching on dropdown (txt)
    return frappe.db.sql("""
        SELECT name, account_name
        FROM `tabAccount`
        WHERE name = %(account)s
          AND (name LIKE %(txt)s OR account_name LIKE %(txt)s)
        LIMIT %(start)s, %(page_len)s
    """, {
        "account": petty_cash_account,
        "txt": "%%%s%%" % txt,
        "start": start,
        "page_len": page_len,
    })

def get_petty_cash_account(company):
    petty_cash_account = frappe.db.get_value(
        "Account", {"account_name": "Petty Cash", "company": company}, "name"
    )
    if petty_cash_account:
        return petty_cash_account
    else:
        frappe.throw(_("Petty Cash account not found for company {0}. Contact Accounts Manager.").format(company))


@frappe.whitelist()
def get_employee_for_petty_cash_user(doctype, txt, searchfield, start, page_len, filters):
    """
    Returns only the employee record linked to the logged-in Petty cash user.
    """
    user = filters.get("user")
    if not user:
        return []

    employee_id = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    if not employee_id:
        return []

    return frappe.db.sql("""
        SELECT name, employee_name
        FROM `tabEmployee`
        WHERE name = %(employee)s
          AND (name LIKE %(txt)s OR employee_name LIKE %(txt)s)
        LIMIT %(start)s, %(page_len)s
    """, {
        "employee": employee_id,
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len,
    })