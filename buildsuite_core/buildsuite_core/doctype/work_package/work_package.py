# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


def _next_wp_code(project):
	"""Next unused WP-NN code within a project (WP-01, WP-02 …)."""
	used = {
		(c or "").upper()
		for c in frappe.get_all("Work Package", filters={"project": project}, pluck="code")
	}
	n = 1
	while f"WP-{n:02d}" in used:
		n += 1
	return f"WP-{n:02d}"


class WorkPackage(Document):
	def before_insert(self):
		# Auto-generate the business code when left blank (the create form promises
		# this). Kept per-project + sequential so it's stable and human-readable.
		if not (self.code or "").strip() and self.project:
			self.code = _next_wp_code(self.project)

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		budget: DF.Currency
		code: DF.Data | None
		description: DF.Text | None
		end_date: DF.Date | None
		progress: DF.Percent
		project: DF.Link
		start_date: DF.Date | None
		status: DF.Literal["Planned", "In Progress", "On Hold", "Completed"]
		work_package_name: DF.Data
	# end: auto-generated types
