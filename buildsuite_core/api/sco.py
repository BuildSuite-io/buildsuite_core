import frappe
from frappe import _
from frappe.utils import now_datetime, today


def _add_activity(doc, action, comment=None):
	doc.append(
		"scope_change_order_activity",
		{
			"action": action,
			"user": frappe.session.user,
			"activity_on": now_datetime(),
			"comment": comment or "",
		},
	)
	doc.save()


# --- workflow -------------------------------------------------------------


@frappe.whitelist()
def approve_sco(sco):
	"""Pending Approval -> Approved."""
	doc = frappe.get_doc("Scope Change Order", sco)
	if doc.status != "Pending Approval":
		frappe.throw(_("Only a pending scope change can be approved."))
	doc.status = "Approved"
	doc.approved_by = frappe.session.user
	doc.approved_date = today()
	doc.rejection_comment = ""
	_add_activity(doc, "approved")
	return doc.status


@frappe.whitelist()
def reject_sco(sco, comment=None):
	"""Pending Approval -> Rejected (comment required)."""
	comment = (comment or "").strip()
	if not comment:
		frappe.throw(_("A reason is required to reject a scope change."))
	doc = frappe.get_doc("Scope Change Order", sco)
	if doc.status != "Pending Approval":
		frappe.throw(_("Only a pending scope change can be rejected."))
	doc.status = "Rejected"
	doc.rejection_comment = comment
	_add_activity(doc, "rejected", comment)
	return doc.status


@frappe.whitelist()
def revise_sco(sco):
	"""Approved / Rejected -> Pending Approval (re-open)."""
	doc = frappe.get_doc("Scope Change Order", sco)
	doc.status = "Pending Approval"
	doc.approved_by = None
	doc.approved_date = None
	doc.rejection_comment = ""
	_add_activity(doc, "revised")
	return doc.status
