# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate

from buildsuite_core.utils.payment_terms import clear_unused_timing
from buildsuite_core.utils.project import anchor_company_to_project

# A tender's lifecycle. Longer than a quotation's: it is submitted, then sits with the client
# while they evaluate it, and only then is awarded or not. Rejected can be reopened as a draft.
TENDER_TRANSITIONS = {
	"Draft": ("Submitted",),
	"Submitted": ("Under Evaluation", "Awarded", "Rejected", "Draft"),
	"Under Evaluation": ("Awarded", "Rejected"),
	"Awarded": (),
	"Rejected": ("Draft",),
}


class BuildSuiteTenders(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.buildsuite_payment_milestone.buildsuite_payment_milestone import (
			BuildSuitePaymentMilestone,
		)
		from buildsuite_core.buildsuite_core.doctype.buildsuite_tender_section.buildsuite_tender_section import (
			BuildSuiteTenderSection,
		)
		from buildsuite_core.buildsuite_core.doctype.buildsuite_tenders_items.buildsuite_tenders_items import (
			BuildSuiteTendersItems,
		)

		bid_before_tax: DF.Currency
		bid_value: DF.Currency
		buildsuite_tenders_items: DF.Table[BuildSuiteTendersItems]
		company: DF.Link | None
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
		payment_milestones: DF.Table[BuildSuitePaymentMilestone]
		payment_term_template: DF.Link | None
		performance_guarantee_percent: DF.Data | None
		portal: DF.Data | None
		preamble_sections: DF.Table[BuildSuiteTenderSection]
		project: DF.Link | None
		project_category: DF.Link | None
		status: DF.Literal["Draft", "Submitted", "Under Evaluation", "Awarded", "Rejected"]
		submission_deadline: DF.Date
		subtotal: DF.Currency
		tax_amount: DF.Currency
		tax_percent: DF.Float
		tender_reference: DF.Data
		terms_sections: DF.Table[BuildSuiteTenderSection]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_lifecycle()
		anchor_company_to_project(self)
		self.items_count = len(self.buildsuite_tenders_items)
		self.validate_dates()
		self.calculate_items()
		clear_unused_timing(self.payment_milestones)

	def validate_lifecycle(self):
		"""The status moves only through set_status (the tender's actions), and only a draft can be
		edited: once submitted, the bid is what was sent, and re-pricing means copying it."""
		if self.flags.tender_status_change:
			return
		if self.is_new():
			self.status = "Draft"
			return
		before = self.get_doc_before_save()
		if not before:
			return
		if self.status != before.status:
			frappe.throw(_("A tender's status changes through its actions, not by editing it."))
		if (before.status or "Draft") != "Draft":
			frappe.throw(
				_("Tender {0} is {1}, so it can't be changed. Copy it to re-price.").format(
					self.name, _(before.status)
				),
				title=_("Tender frozen"),
			)

	def set_status(self, status):
		"""Move the tender to `status`, if its lifecycle allows it from the current one."""
		current = self.status or "Draft"
		if status not in TENDER_TRANSITIONS.get(current, ()):
			frappe.throw(
				_("A tender can't go from {0} to {1}.").format(_(current), _(status)),
				title=_("Not allowed"),
			)
		self.status = status
		self.flags.tender_status_change = True
		self.save()

	def on_trash(self):
		if self.status == "Awarded":
			frappe.throw(_("Tender {0} won the work, so it can't be deleted.").format(self.name))

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
