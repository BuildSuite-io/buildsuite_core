# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BuildSuiteTenders(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.buildsuite_tenders_items.buildsuite_tenders_items import BuildSuiteTendersItems
		from frappe.types import DF

		buildsuite_tenders_items: DF.Table[BuildSuiteTendersItems]
		date_issued: DF.Date | None
		emd_amount: DF.Currency
		emd_instrument: DF.Data | None
		emd_valid_until: DF.Date | None
		envelope_structure: DF.Literal["Single", "Two-envelope", "Three-envelope"]
		issued_by: DF.Literal["Government", "Main Contractor"]
		issuing_body: DF.Data
		items_count: DF.Int
		margin_percent: DF.Float
		notes: DF.SmallText | None
		performance_guarantee_percent: DF.Data | None
		portal: DF.Data | None
		project: DF.Link | None
		submission_deadline: DF.Date
		tax_percent: DF.Float
		tender_reference: DF.Data
		title: DF.Data
	# end: auto-generated types

	def validate(self):

		self.items_count = len(self.buildsuite_tenders_items)
