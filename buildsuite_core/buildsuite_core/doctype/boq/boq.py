# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

from buildsuite_core.buildsuite_core.doctype.boq.boq_rollup import compute_boq_totals


class BOQ(Document):
	def before_insert(self):
		if self.project and not self.company:
			self.company = frappe.db.get_value("Project", self.project, "company")
		if not self.prepared_by:
			self.prepared_by = frappe.session.user
		if not self.prepared_date:
			self.prepared_date = today()
		if not self.status:
			self.status = "Draft"
		if not self.revision:
			self.revision = 1

	def validate(self):
		if self.project and not self.company:
			self.company = frappe.db.get_value("Project", self.project, "company")
		compute_boq_totals(self)

	def on_trash(self):
		# Cascade-delete the whole tree (sub-items first, then items, then groups).
		for doctype in ("BOQ Sub Item", "BOQ Item", "BOQ Group"):
			for name in frappe.get_all(doctype, filters={"boq": self.name}, pluck="name"):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
