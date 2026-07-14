# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, today


class ScopeChangeOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.scope_change_order_activity.scope_change_order_activity import ScopeChangeOrderActivity
		from frappe.types import DF

		approved_by: DF.Link | None
		approved_date: DF.Date | None
		company: DF.Link | None
		cost_impact: DF.Currency
		cost_recovery: DF.Literal["Recoverable from Client", "Internal"]
		project: DF.Link
		raised_by: DF.Link | None
		raised_date: DF.Date | None
		reason__justification: DF.SmallText | None
		rejection_comment: DF.SmallText | None
		sco_type: DF.Literal["Design Change", "Client Request", "Statutory", "Site Condition", "Rework", "Other"]
		scope_change_order_activity: DF.Table[ScopeChangeOrderActivity]
		status: DF.Literal["Pending Approval", "Approved", "Rejected"]
		title: DF.Data
	# end: auto-generated types

	def before_insert(self):
		# Raise = submit for approval (matches the prototype). Stamp who/when and
		# open the activity log with a "raised" entry. company is auto-fetched via
		# the field's fetch_from = project.company.
		self.raised_by = self.raised_by or frappe.session.user
		self.raised_date = self.raised_date or today()
		self.status = self.status or "Pending Approval"
		self.append(
			"scope_change_order_activity",
			{"action": "raised", "user": self.raised_by, "activity_on": now_datetime()},
		)
