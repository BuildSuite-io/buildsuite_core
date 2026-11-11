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
		from buildsuite_core.buildsuite_core.doctype.construction_rate_history.construction_rate_history import ConstructionRateHistory
		from frappe.types import DF

		category: DF.Literal["Material", "Labour", "Equipment", "Others"]
		current_rate: DF.Currency
		disabled: DF.Check
		effective_date: DF.Date | None
		notes: DF.SmallText | None
		previous_rate: DF.Currency
		rate_code: DF.Data
		rate_history: DF.Table[ConstructionRateHistory]
		rate_master_category: DF.Link | None
		rate_name: DF.Data
		uom: DF.Link
	# end: auto-generated types

	def validate(self):
		self.sync_rate_history()

	def on_update(self):
		# A new rate reaches every assembly built from this resource, so an assembly's live
		# rate_per_unit never lags the Rate Master. Estimates and quotations keep the snapshot
		# they took (their lines store the rate), so nothing already priced changes.
		if not self.is_new() and self.has_value_changed("current_rate"):
			self.reprice_assemblies()

	def reprice_assemblies(self):
		parents = frappe.get_all(
			"Assembly Component",
			filters={"resource": self.name, "parenttype": "Assembly"},
			pluck="parent",
			distinct=True,
		)
		for name in parents:
			assembly = frappe.get_doc("Assembly", name)
			assembly.flags.ignore_permissions = True
			assembly.save()

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
			source = self.flags.get("rate_source") or {}
			reason = "Purchase-driven" if source.get("purchase_order") else "Manual revision"
			self._append_rate_row(reason, today, source)

	def _close_open_row(self, effective_to):
		for row in self.rate_history:
			if not row.effective_to:
				row.effective_to = effective_to

	def _append_rate_row(self, reason, effective_from, source=None):
		source = source or {}
		row = {
			"rate": self.current_rate,
			"effective_from": effective_from,
			"effective_to": None,
			"reason": reason,
			"changed_by": frappe.session.user,
			"changed_on": now_datetime(),
		}
		if source.get("purchase_order"):
			row["purchase_order"] = source["purchase_order"]
		if source.get("supplier"):
			row["supplier"] = source["supplier"]
		self.append("rate_history", row)
