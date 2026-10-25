# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from buildsuite_core.utils.payment_terms import clear_unused_timing


class BuildSuitePaymentTermTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.buildsuite_payment_milestone.buildsuite_payment_milestone import BuildSuitePaymentMilestone
		from frappe.types import DF

		description: DF.SmallText | None
		enabled: DF.Check
		milestones: DF.Table[BuildSuitePaymentMilestone]
		milestones_count: DF.Int
		payment_term_name: DF.Data
		project_category: DF.Link | None
		total_percentage: DF.Percent
	# end: auto-generated types

	def validate(self):
		clear_unused_timing(self.milestones)
		self.milestones_count = len(self.milestones)
		self.total_percentage = sum(flt(row.percentage) for row in self.milestones)
		self._validate_total()

	def _validate_total(self):
		if self.milestones and abs(self.total_percentage - 100) > 0.01:
			frappe.throw(
				_("Milestones must add up to 100%. They add up to {0}%.").format(self.total_percentage)
			)
