# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BuildSuitePaymentMilestone(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		client_sign_off: DF.Check
		days_after_project_start: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payable: DF.Literal["On signing", "Stage completes", "On a date", "Running bills"]
		payment_milestone: DF.Data | None
		percentage: DF.Percent
		stage: DF.Data | None
	# end: auto-generated types

	pass
