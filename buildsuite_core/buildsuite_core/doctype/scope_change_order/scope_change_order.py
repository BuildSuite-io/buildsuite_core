# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today

from buildsuite_core.utils.project import anchor_company_to_project, assert_same_company


class ScopeChangeOrder(Document):
	def validate(self):
		self._set_company()
		if not self.raised_by:
			self.raised_by = frappe.session.user
		if not self.raised_date:
			self.raised_date = today()
		if not self.status:
			self.status = "Pending Approval"
		# A rejection must always carry a reason — guards any path that lands the doc in
		# Rejected (the reject_sco endpoint, or a direct Desk workflow "Reject" action).
		if self.status == "Rejected" and not (self.rejection_reason or "").strip():
			frappe.throw(_("A rejection reason is required to reject this change order."))

	def before_save(self):
		# Approve / Reject / Revise are now Frappe Workflow transitions (workflow bound to the
		# `status` field). Their side effects — approver + date stamping, reason capture, the
		# audit-trail row — live here so they fire on the state change regardless of whether it
		# was driven by api/sco.py's apply_workflow or a direct Desk workflow action. Runs in
		# before_save so the appended child row is persisted with the same write.
		before = self.get_doc_before_save()
		if not before or before.status == self.status:
			return
		self._on_status_change(self.status)

	def _on_status_change(self, new_status):
		if new_status == "Approved":
			self.approved_by = frappe.session.user
			self.approved_date = today()
			self.rejection_reason = None
			self._add_activity("Approved")
		elif new_status == "Rejected":
			self._add_activity("Rejected", self.rejection_reason)
		elif new_status == "Pending Approval":  # Revise — reopened for edit / re-submission
			self.approved_by = None
			self.approved_date = None
			self.rejection_reason = None
			self._add_activity("Revised")

	def _add_activity(self, action, comment=None):
		"""Append an audit-trail row (who did what, when) to the change order."""
		self.append(
			"scope_change_order_activity",
			{
				"action": action,
				"user": frappe.session.user,
				"activity_on": now_datetime(),
				"comment": comment,
			},
		)

	def _set_company(self):
		# Anchor to the project's company (always re-derive), then block a BOQ revision that
		# belongs to another company's project — the core cross-company guard.
		anchor_company_to_project(self)
		assert_same_company(self, "boq_revision", "BOQ", label="BOQ")
