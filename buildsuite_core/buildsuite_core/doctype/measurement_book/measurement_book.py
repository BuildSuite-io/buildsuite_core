# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from buildsuite_core.utils.project import anchor_company_to_project, assert_same_company


class MeasurementBook(Document):
	def validate(self):
		self._default_project_from_wo()
		self._compute_quantities()
		self._set_company()
		if not self.status:
			self.status = "Draft"

	def _default_project_from_wo(self):
		if self.work_order and not self.project:
			self.project = frappe.db.get_value("Subcontractor Work Order", self.work_order, "project")

	def _compute_quantities(self):
		"""Derive each entry's quantity from Nos x L x B x D when it isn't given
		directly, then roll the (signed) entry quantities into measured_total."""
		total = 0.0
		for row in self.entries:
			if not flt(row.quantity):
				derived = flt(row.nos) * flt(row.length) * flt(row.breadth) * flt(row.depth)
				row.quantity = round(derived, 3)
			total += (-1 if row.is_deduction else 1) * flt(row.quantity)
		self.measured_total = total

	def _set_company(self):
		# Anchor to the project's company (always re-derive), then block a Work Order that
		# belongs to a different company's project from being measured/certified here.
		anchor_company_to_project(self)
		assert_same_company(self, "work_order", "Subcontractor Work Order", label="Work Order")
