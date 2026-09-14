# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

from buildsuite_core.buildsuite_core.doctype.boq.boq_rollup import compute_boq_totals
from buildsuite_core.utils.project import anchor_company_to_project, assert_same_company


class BOQ(Document):
	def before_insert(self):
		anchor_company_to_project(self)
		if not self.prepared_by:
			self.prepared_by = frappe.session.user
		if not self.prepared_date:
			self.prepared_date = today()
		if not self.status:
			self.status = "Draft"
		if not self.revision:
			self.revision = 1

	def validate(self):
		# Company is anchored to the project; a BOQ derived from another BOQ (base_revision)
		# must share the same company — blocks cross-company revision chains.
		anchor_company_to_project(self)
		assert_same_company(self, "base_revision", "BOQ", label="BOQ")
		compute_boq_totals(self)

	def on_trash(self):
		# Cascade-delete the whole tree (sub-items first, then items, then groups).
		for doctype in ("BOQ Sub Item", "BOQ Item", "BOQ Group"):
			for name in frappe.get_all(doctype, filters={"boq": self.name}, pluck="name"):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
