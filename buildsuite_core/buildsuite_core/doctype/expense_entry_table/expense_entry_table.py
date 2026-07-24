# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ExpenseEntryTable(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		attachment: DF.Attach | None
		cost_center: DF.Link | None
		description: DF.SmallText | None
		employee: DF.Link | None
		employee_name: DF.Data | None
		expense_account: DF.Link
		expense_account_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_account: DF.Link
		payment_account_name: DF.Data | None
		project: DF.Link | None
		project_name: DF.Data | None
	# end: auto-generated types

	pass
