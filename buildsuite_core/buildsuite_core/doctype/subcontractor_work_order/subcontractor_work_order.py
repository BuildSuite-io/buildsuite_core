# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SubcontractorWorkOrder(Document):
	def validate(self):
		self._compute_totals()
		self._set_company()
		if not self.status:
			self.status = "Draft"

	def _compute_totals(self):
		total = 0.0
		for row in self.lines:
			row.amount = flt(row.qty) * flt(row.rate)
			total += flt(row.amount)
		self.total_value = total

	def _set_company(self):
		if self.company:
			return
		if self.project:
			self.company = frappe.db.get_value("Project", self.project, "company")
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
