# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate


class BuildSuiteTenders(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.buildsuite_tender_section.buildsuite_tender_section import BuildSuiteTenderSection
		from buildsuite_core.buildsuite_core.doctype.buildsuite_tenders_items.buildsuite_tenders_items import BuildSuiteTendersItems
		from frappe.types import DF

		bid_before_tax: DF.Currency
		bid_value: DF.Currency
		buildsuite_tenders_items: DF.Table[BuildSuiteTendersItems]
		date_issued: DF.Date | None
		emd_amount: DF.Currency
		emd_instrument: DF.Data | None
		emd_valid_until: DF.Date | None
		envelope_structure: DF.Literal["Single", "Two-envelope", "Three-envelope"]
		issued_by: DF.Literal["Government", "Main Contractor"]
		issuing_body: DF.Data
		items_count: DF.Int
		margin_amount: DF.Currency
		margin_percent: DF.Float
		notes: DF.SmallText | None
		performance_guarantee_percent: DF.Data | None
		portal: DF.Data | None
		preamble_sections: DF.Table[BuildSuiteTenderSection]
		project: DF.Link | None
		submission_deadline: DF.Date
		subtotal: DF.Currency
		tax_amount: DF.Currency
		tax_percent: DF.Float
		tender_reference: DF.Data
		terms_sections: DF.Table[BuildSuiteTenderSection]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.items_count = len(self.buildsuite_tenders_items)
		self.validate_dates()
		self.calculate_items()

	def calculate_items(self):
		# Sell rate is the cost rate plus the margin; the amount is the qty at that sell rate.
		margin = 1 + flt(self.margin_percent) / 100
		for row in self.buildsuite_tenders_items:
			row.sell_rate = flt(row.rate) * margin
			row.amount = flt(row.qty) * flt(row.sell_rate)

		# Totals are stored, not just derived in the detail view — a list column or a report
		# reads the parent row only, and cannot reach the item rows to add them up.
		self.subtotal = sum(flt(row.qty) * flt(row.rate) for row in self.buildsuite_tenders_items)
		self.bid_before_tax = sum(flt(row.amount) for row in self.buildsuite_tenders_items)
		self.margin_amount = flt(self.bid_before_tax) - flt(self.subtotal)
		# Tax is charged on the price the client pays, never on our cost.
		self.tax_amount = flt(self.bid_before_tax) * flt(self.tax_percent) / 100
		self.bid_value = flt(self.bid_before_tax) + flt(self.tax_amount)

	def validate_dates(self):
		# A deadline before the invitation was issued is a typo, not a tender.
		if self.date_issued and self.submission_deadline:
			if getdate(self.submission_deadline) < getdate(self.date_issued):
				frappe.throw(
					_("Submission deadline ({0}) can't be before the date issued ({1}).").format(
						formatdate(self.submission_deadline), formatdate(self.date_issued)
					),
					title=_("Invalid dates"),
				)
