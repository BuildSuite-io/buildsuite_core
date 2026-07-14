# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

WORK_ORDER = "Subcontractor Work Order"


def previously_billed_by_line(work_order, exclude_bill=None):
	"""Sum of `this_period_qty` already claimed on each SOV line by the WO's other
	SUBMITTED Subcontractor Bills. Used to derive a fresh bill's this-period qty
	(measured-to-date minus what earlier bills already billed)."""
	bills = frappe.get_all(
		"Subcontractor Bill",
		filters={"work_order": work_order, "docstatus": 1},
		pluck="name",
	)
	if exclude_bill and exclude_bill in bills:
		bills.remove(exclude_bill)
	out = {}
	if not bills:
		return out
	rows = frappe.get_all(
		"Subcontractor Bill Line",
		filters={"parent": ["in", bills]},
		fields=["work_order_line", "this_period_qty"],
	)
	for r in rows:
		key = r.work_order_line or ""
		out[key] = out.get(key, 0) + flt(r.this_period_qty)
	return out


class SubcontractorBill(Document):
	def validate(self):
		self._require_open_work_order()
		self._assign_ra_no()
		self._compute_totals()
		self._sync_status()

	def before_submit(self):
		if not self.lines:
			frappe.throw(_("Add at least one line — use 'Fetch from Work Order' to derive this period's quantities."))
		if flt(self.gross) <= 0:
			frappe.throw(_("Nothing to bill: this period's quantity is zero. Certify a Measurement Book first."))

	def on_submit(self):
		self._sync_status()

	def on_cancel(self):
		self._sync_status()

	# --- helpers ----------------------------------------------------------

	def _require_open_work_order(self):
		status = frappe.db.get_value(WORK_ORDER, self.work_order, "status")
		if status not in ("Awarded", "In Progress"):
			frappe.throw(
				_("A bill can only be raised against an Awarded or In Progress work order (this one is {0}).").format(
					status or "—"
				)
			)

	def _assign_ra_no(self):
		if self.ra_no:
			return
		existing = frappe.get_all(
			"Subcontractor Bill",
			filters={"work_order": self.work_order, "docstatus": ["<", 2], "name": ["!=", self.name or ""]},
			pluck="ra_no",
		)
		self.ra_no = max([r for r in existing if r] or [0]) + 1

	def _compute_totals(self):
		gross = 0.0
		for row in self.lines:
			row.this_period_amount = flt(row.this_period_qty) * flt(row.rate)
			gross += flt(row.this_period_amount)
		self.gross = gross
		self.retention_amount = flt(gross) * flt(self.retention_percent) / 100.0
		self.net_payable = flt(gross) - flt(self.retention_amount)

	def _sync_status(self):
		# Payment ("Paid") arrives with the accounting pass; for now status mirrors docstatus.
		self.status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(self.docstatus, "Draft")

	@frappe.whitelist()
	def fetch_lines(self):
		"""Rebuild the bill lines from the Work Order's schedule of values, deriving
		this-period qty = certified measured-to-date - previously billed, per line."""
		from buildsuite_core.api.subcontract import get_wo_measurements

		if not self.work_order:
			frappe.throw(_("Select a Work Order first."))

		measured = get_wo_measurements(self.work_order).get("measured_by_line", {})
		previous = previously_billed_by_line(self.work_order, exclude_bill=self.name)
		wo = frappe.get_doc(WORK_ORDER, self.work_order)

		self.set("lines", [])
		for row in wo.lines:
			m = flt(measured.get(row.name, 0))
			p = flt(previous.get(row.name, 0))
			tpq = max(0.0, m - p)
			self.append(
				"lines",
				{
					"work_order_line": row.name,
					"scope": row.scope,
					"cost_code_type": row.cost_code_type,
					"cost_code_group": row.cost_code_group,
					"cost_code_item": row.cost_code_item,
					"cost_code_label": row.cost_code_label,
					"uom": row.uom,
					"rate": row.rate,
					"measured_qty_to_date": m,
					"previous_qty": p,
					"this_period_qty": tpq,
					"this_period_amount": tpq * flt(row.rate),
				},
			)
		self._compute_totals()
		return self.as_dict()
