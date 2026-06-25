# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EstimateTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.estimate_template_row.estimate_template_row import (
			EstimateTemplateRow,
		)

		description: DF.SmallText | None
		enabled: DF.Check
		estimated_total: DF.Currency
		project_type: DF.Link | None
		row_count: DF.Int
		rows: DF.Table[EstimateTemplateRow]
		template_code: DF.Data
		template_name: DF.Data
	# end: auto-generated types

	def validate(self):
		total = 0
		for row in self.rows:
			total += self._sync_row(row)
		self.estimated_total = total
		self.row_count = len(self.rows)

	def _sync_row(self, row):
		"""Derive each row's uom + description from the linked Assembly /
		Resource, clear the unused link, and return the row amount
		(qty * current rate) so validate() can roll up estimated_total.
		"""
		if row.line_type == "Assembly":
			row.resource = None
			if not row.assembly:
				frappe.throw(
					frappe._("Row #{0}: Assembly is required when Line Type is Assembly.").format(row.idx)
				)
			name, uom, rate = frappe.db.get_value(
				"Assembly", row.assembly, ["assembly_name", "uom", "rate_per_unit"]
			) or (None, None, 0)
		elif row.line_type == "Resource":
			row.assembly = None
			if not row.resource:
				frappe.throw(
					frappe._("Row #{0}: Resource is required when Line Type is Resource.").format(row.idx)
				)
			name, uom, rate = frappe.db.get_value(
				"Construction Rate Master", row.resource, ["rate_name", "uom", "current_rate"]
			) or (None, None, 0)
		else:
			return 0

		row.uom = uom
		row.description = name
		row.rate = rate or 0
		row.amount = (row.placeholder_qty or 0) * (rate or 0)
		return row.amount
