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
		self._sync_from_work_order()
		if self.work_order and not self.is_direct:
			self._require_open_work_order()
		self._assign_ra_no()
		self._default_expense_account()
		self._validate_account_companies()
		self._resolve_tds_rate()
		self._compute_totals()
		self._sync_status()

	def _default_expense_account(self):
		if self.expense_account or not self.company:
			return
		from buildsuite_core.utils.subcontract_billing import settings_expense_account_for

		self.expense_account = settings_expense_account_for(self.company)

	def _validate_account_companies(self):
		"""The tax template, tax-row accounts and expense account must all belong to the bill's
		company (which is anchored to the project). Caught here with a clear message rather than
		as a cryptic Purchase Invoice error on submit — the generated PI validates the same."""
		if not self.company:
			return

		def _belongs(account, doctype="Account"):
			company = frappe.db.get_value(doctype, account, "company")
			return not company or company == self.company

		if self.taxes_and_charges and not _belongs(self.taxes_and_charges, "Purchase Taxes and Charges Template"):
			frappe.throw(
				_("Tax template {0} belongs to a different company — pick one for {1} (this project's company).").format(
					frappe.bold(self.taxes_and_charges), frappe.bold(self.company)
				)
			)
		for t in self.taxes:
			if t.account_head and not _belongs(t.account_head):
				frappe.throw(
					_("Tax row #{0}: account {1} does not belong to company {2}.").format(
						t.idx, frappe.bold(t.account_head), frappe.bold(self.company)
					)
				)
		if self.expense_account and not _belongs(self.expense_account):
			frappe.throw(
				_("Expense account {0} does not belong to company {1}.").format(
					frappe.bold(self.expense_account), frappe.bold(self.company)
				)
			)

	def before_submit(self):
		if not self.lines:
			frappe.throw(_("Add at least one line before submitting."))
		if flt(self.gross) <= 0:
			frappe.throw(_("Nothing to bill: this period's value is zero."))
		if not self.subcontractor:
			frappe.throw(_("A subcontractor is required."))

	def on_submit(self):
		from buildsuite_core.utils.subcontract_billing import generate_purchase_invoice

		self.purchase_invoice = generate_purchase_invoice(self)
		self.db_set("purchase_invoice", self.purchase_invoice)
		self._sync_status()

	def on_cancel(self):
		self._cancel_purchase_invoice()
		self._sync_status()

	# --- helpers ----------------------------------------------------------

	def _sync_from_work_order(self):
		"""WO bills inherit party/project/retention from the Work Order. Direct bills carry
		their own (subcontractor + project entered on the form)."""
		if self.work_order and not self.is_direct:
			wo = frappe.db.get_value(
				WORK_ORDER,
				self.work_order,
				["subcontractor", "subcontractor_name", "project", "retention_percent"],
				as_dict=True,
			)
			if wo:
				self.subcontractor = wo.subcontractor
				self.subcontractor_name = wo.subcontractor_name
				self.project = wo.project
				if self.retention_percent in (None, ""):
					self.retention_percent = wo.retention_percent
		elif self.subcontractor and not self.subcontractor_name:
			self.subcontractor_name = frappe.db.get_value("Supplier", self.subcontractor, "supplier_name")

		# Company is anchored to the PROJECT (the accounting dimension the generated PI
		# validates against), never the Work Order — a WO whose company drifted from its
		# project's would otherwise make the PI reject the project dimension.
		if self.project:
			self.company = frappe.db.get_value("Project", self.project, "company")

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
		# WO bills sequence per work order; direct bills sequence per subcontractor.
		if self.work_order and not self.is_direct:
			scope = {"work_order": self.work_order}
		else:
			scope = {"subcontractor": self.subcontractor, "is_direct": 1}
		existing = frappe.get_all(
			"Subcontractor Bill",
			filters={**scope, "docstatus": ["<", 2], "name": ["!=", self.name or ""]},
			pluck="ra_no",
		)
		self.ra_no = max([r for r in existing if r] or [0]) + 1

	def _resolve_tds_rate(self):
		"""Best-effort withholding rate for the PREVIEW waterfall, read from the chosen
		Tax Withholding Category. The authoritative TDS is computed by ERPNext on the PI."""
		self.tds_rate = 0
		if not (self.apply_tds and self.tax_withholding_category):
			return
		rows = frappe.get_all(
			"Tax Withholding Rate",
			filters={"parent": self.tax_withholding_category},
			fields=["tax_withholding_rate", "from_date", "to_date"],
		)
		rate = 0
		for r in rows:
			if r.from_date and self.date and str(r.from_date) <= str(self.date) and (
				not r.to_date or str(self.date) <= str(r.to_date)
			):
				rate = flt(r.tax_withholding_rate)
				break
		if not rate and rows:
			rate = flt(rows[0].tax_withholding_rate)
		self.tds_rate = rate

	def _compute_totals(self):
		"""The prototype waterfall: gross → (net discount) → taxable → +taxes → grand total
		→ (grand discount) → invoice value → −tds −retention −advance → net payable."""
		gross = 0.0
		for row in self.lines:
			# WO lines carry qty×rate; direct lines carry a typed amount only.
			if flt(row.this_period_qty) and flt(row.rate):
				row.this_period_amount = flt(row.this_period_qty) * flt(row.rate)
			gross += flt(row.this_period_amount)
		self.gross = gross

		net_discount = grand_discount = 0.0
		disc_pct = flt(self.additional_discount_percentage)
		disc_amt = flt(self.discount_amount)
		if self.additional_discount_on == "Net Total":
			net_discount = disc_amt or (gross * disc_pct / 100.0)
		elif self.additional_discount_on == "Grand Total":
			grand_discount = disc_amt  # % on grand total resolved below once grand known

		self.taxable_value = max(0.0, gross - net_discount)

		total_taxes = 0.0
		for t in self.taxes:
			t.tax_amount = flt(self.taxable_value) * flt(t.rate) / 100.0
			total_taxes += flt(t.tax_amount)
		self.total_taxes = total_taxes
		self.grand_total = flt(self.taxable_value) + total_taxes

		if self.additional_discount_on == "Grand Total" and not grand_discount:
			grand_discount = flt(self.grand_total) * disc_pct / 100.0
		self.invoice_value = max(0.0, flt(self.grand_total) - grand_discount)

		self.tds_amount = flt(self.taxable_value) * flt(self.tds_rate) / 100.0 if self.apply_tds else 0.0
		self.retention_amount = flt(self.taxable_value) * flt(self.retention_percent) / 100.0
		self.net_payable = max(
			0.0,
			flt(self.invoice_value)
			- flt(self.tds_amount)
			- flt(self.retention_amount)
			- flt(self.advance_recovery),
		)

	def _sync_status(self):
		self.status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(self.docstatus, "Draft")

	def _cancel_purchase_invoice(self):
		if not self.purchase_invoice:
			return
		pi = frappe.db.exists("Purchase Invoice", self.purchase_invoice)
		if not pi:
			return
		doc = frappe.get_doc("Purchase Invoice", self.purchase_invoice)
		if doc.docstatus == 1:
			paid = flt(doc.grand_total) - flt(doc.outstanding_amount)
			if paid > 0:
				frappe.throw(
					_("This bill's Purchase Invoice has payments against it. Cancel the Payment Entries first.")
				)
			doc.flags.ignore_permissions = True
			doc.cancel()

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
