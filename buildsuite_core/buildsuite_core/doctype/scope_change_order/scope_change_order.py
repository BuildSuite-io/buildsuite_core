# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

from buildsuite_core.utils.project import anchor_company_to_project, assert_same_company


class ScopeChangeOrder(Document):
	def validate(self):
		self._set_company()
		if not self.raised_by:
			self.raised_by = frappe.session.user
		if not self.raised_date:
			self.raised_date = today()
		if not self.status:
			self.status = "Pending Approval"

	def _set_company(self):
		# Anchor to the project's company (always re-derive), then block a BOQ revision that
		# belongs to another company's project — the core cross-company guard.
		anchor_company_to_project(self)
		assert_same_company(self, "boq_revision", "BOQ", label="BOQ")
