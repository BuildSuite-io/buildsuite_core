# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The Subcontractor Work Order became natively submittable — state is docstatus now, not the old
approval `status` field/Workflow. Runs BEFORE model sync so the `status` column still exists:
retire the approval Workflow and map the legacy status onto docstatus before the column is dropped.
Committed states (Awarded / In Progress / Closed) → Submitted (docstatus 1); Draft / Pending
Approval stay Draft (docstatus 0)."""

import frappe


def execute():
	if frappe.db.exists("Workflow", "Subcontractor Work Order Approval"):
		frappe.delete_doc(
			"Workflow", "Subcontractor Work Order Approval", ignore_permissions=True, force=True
		)

	if frappe.db.has_column("Subcontractor Work Order", "status"):
		frappe.db.sql(
			"""
			UPDATE `tabSubcontractor Work Order`
			SET docstatus = 1
			WHERE docstatus = 0 AND status IN ('Awarded', 'In Progress', 'Closed')
			"""
		)
