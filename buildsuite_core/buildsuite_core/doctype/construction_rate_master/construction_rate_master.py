# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate


class ConstructionRateMaster(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.construction_rate_history.construction_rate_history import (
			ConstructionRateHistory,
		)

		category: DF.Literal["Material", "Labour", "Equipment"]
		current_rate: DF.Currency
		disabled: DF.Check
		effective_date: DF.Date | None
		notes: DF.SmallText | None
		rate_code: DF.Data
		rate_history: DF.Table[ConstructionRateHistory]
		rate_name: DF.Data
		uom: DF.Link
	# end: auto-generated types

	def validate(self):
		self.sync_rate_history()

	def sync_rate_history(self):
		today = nowdate()
		if self.is_new():
			self.effective_date = today
			self._append_rate_row("Initial", today)
			return

		if self.has_value_changed("current_rate"):
			before = self.get_doc_before_save()
			if before:
				self.previous_rate = before.current_rate
			self.effective_date = today
			self._close_open_row(today)
			self._append_rate_row("Manual revision", today)

	def _close_open_row(self, effective_to):
		for row in self.rate_history:
			if not row.effective_to:
				row.effective_to = effective_to

	def _append_rate_row(self, reason, effective_from):
		self.append(
			"rate_history",
			{
				"rate": self.current_rate,
				"effective_from": effective_from,
				"effective_to": None,
				"reason": reason,
				"changed_by": frappe.session.user,
				"changed_on": now_datetime(),
			},
		)
