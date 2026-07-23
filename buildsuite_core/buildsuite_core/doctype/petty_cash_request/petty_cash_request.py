# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class PettyCashRequest(Document):
	def validate(self):
		# Company is anchored to the project (the accounting dimension the Journal Entry posts
		# against) — never a stale/default value.
		if self.project:
			self.company = frappe.db.get_value("Project", self.project, "company")
		if not self.requested_by:
			self.requested_by = frappe.session.user

	def on_trash(self):
		if self.status == "Disbursed":
			frappe.throw(_("A disbursed request can't be deleted — cancel the disbursement first."))

	# --- actions ----------------------------------------------------------
	def disburse(self, paid_from):
		"""Record the cash going out to the holder and post the Journal Entry."""
		from buildsuite_core.utils.petty_cash import post_disbursement_journal_entry

		if self.status != "Requested":
			frappe.throw(_("Only a Requested petty cash request can be disbursed (this is {0}).").format(self.status))
		if not paid_from:
			frappe.throw(_("Select the cash/bank account to pay from."))
		acc = frappe.db.get_value("Account", paid_from, ["company", "account_type", "is_group"], as_dict=True)
		if not acc or acc.is_group:
			frappe.throw(_("Pick a valid ledger account."))
		if acc.company != self.company:
			frappe.throw(_("Account {0} does not belong to company {1}.").format(paid_from, self.company))

		self.paid_from = paid_from
		self.disbursed_by = frappe.session.user
		self.disbursed_on = now_datetime()
		self.journal_entry = post_disbursement_journal_entry(self)
		self.status = "Disbursed"
		self.save(ignore_permissions=True)
		self.add_comment("Comment", _("Disbursed {0} from {1}").format(frappe.format(flt(self.amount), {"fieldtype": "Currency"}), paid_from))

	def cancel_disbursement(self):
		"""Reverse a disbursement — cancel the Journal Entry and revert to Requested."""
		from buildsuite_core.utils.petty_cash import cancel_disbursement_journal_entry

		if self.status != "Disbursed":
			frappe.throw(_("Only a disbursed request can be reversed."))
		cancel_disbursement_journal_entry(self)
		self.status = "Requested"
		self.paid_from = None
		self.disbursed_by = None
		self.disbursed_on = None
		self.journal_entry = None
		self.save(ignore_permissions=True)
		self.add_comment("Comment", _("Disbursement reversed"))
