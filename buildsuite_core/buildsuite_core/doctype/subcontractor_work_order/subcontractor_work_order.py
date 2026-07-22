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
