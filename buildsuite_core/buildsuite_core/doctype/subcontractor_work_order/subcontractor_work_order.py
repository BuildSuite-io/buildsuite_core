# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SubcontractorWorkOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.subcontractor_work_order_line.subcontractor_work_order_line import (
			SubcontractorWorkOrderLine,
		)

		amended_from: DF.Link | None
		company: DF.Link | None
		date: DF.Date
		delivery_type: DF.Link | None
		lines: DF.Table[SubcontractorWorkOrderLine]
		project: DF.Link
		retention_percent: DF.Percent
		subcontractor: DF.Link
		subcontractor_name: DF.Data | None
		terms: DF.TextEditor | None
		terms_template: DF.Link | None
		total_value: DF.Currency
	# end: auto-generated types

	def validate(self):
		self._compute_totals()
		self._set_company()

	def before_cancel(self):
		# A committed WO can only be cancelled if nothing has been claimed against it — cancelling
		# would strand the Measurement Books / Bills that reference it.
		mbs = frappe.db.count("Measurement Book", {"work_order": self.name, "docstatus": ["<", 2]})
		bills = frappe.db.count("Subcontractor Bill", {"work_order": self.name, "docstatus": ["<", 2]})
		if mbs or bills:
			frappe.throw(
				_(
					"Cannot cancel {0}: it has {1} measurement book(s) and {2} bill(s) against it. Remove those first."
				).format(self.name, mbs, bills)
			)

	def _compute_totals(self):
		total = 0.0
		for row in self.lines:
			row.amount = flt(row.qty) * flt(row.rate)
			total += flt(row.amount)
		self.total_value = total

	def _set_company(self):
		# Company is ANCHORED to the project's company — the accounting company the bill's
		# generated Purchase Invoice validates the project against. Always re-derive it (never
		# just when blank) so a stale value or the user's default company can't drift away from
		# the project and later break PI posting. Only fall back to a default when there's no
		# project yet.
		if self.project:
			project_company = frappe.db.get_value("Project", self.project, "company")
			if not project_company:
				frappe.throw(frappe._("Project {0} has no company set.").format(self.project))
			self.company = project_company
		elif not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
