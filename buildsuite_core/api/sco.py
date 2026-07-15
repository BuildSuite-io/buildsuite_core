# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Scope Change Order approval flow (approve / reject /
revise) and the BOQ-revision tie-in raised from an approved change order. Reads +
plain CRUD go through the standard data adapter; only these transitions need the API."""

import frappe
from frappe import _
from frappe.utils import today

from buildsuite_core.permissions.setup import BOQ_APPROVE_ROLES

SCO = "Scope Change Order"


def _require_approver():
	if not set(frappe.get_roles()) & set(BOQ_APPROVE_ROLES):
		frappe.throw(_("You are not permitted to approve or reject a scope change order."), frappe.PermissionError)


@frappe.whitelist()
def approve_sco(name: str):
	"""Pending Approval -> Approved. Stamps the approver + date."""
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	_require_approver()
	if doc.status != "Pending Approval":
		frappe.throw(_("Only a Pending Approval change order can be approved."))
	doc.status = "Approved"
	doc.approved_by = frappe.session.user
	doc.approved_date = today()
	doc.rejection_reason = None
	doc.save()
	return doc.status


@frappe.whitelist()
def reject_sco(name: str, reason: str = None):
	"""Pending Approval -> Rejected. Records the rejection reason."""
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	_require_approver()
	if doc.status != "Pending Approval":
		frappe.throw(_("Only a Pending Approval change order can be rejected."))
	doc.status = "Rejected"
	doc.rejection_reason = reason
	doc.save()
	return doc.status


@frappe.whitelist()
def revise_sco(name: str):
	"""Approved / Rejected -> Pending Approval, so it can be edited and re-submitted."""
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	if doc.status not in ("Approved", "Rejected"):
		frappe.throw(_("Only an Approved or Rejected change order can be revised."))
	doc.status = "Pending Approval"
	doc.approved_by = None
	doc.approved_date = None
	doc.rejection_reason = None
	doc.save()
	return doc.status


def _project_source_boq(project):
	"""The BOQ a revision should branch from: the Approved one, else the latest
	non-superseded revision."""
	boqs = frappe.get_all(
		"BOQ",
		filters={"project": project},
		fields=["name", "status", "revision"],
		order_by="revision desc",
	)
	if not boqs:
		return None
	approved = next((b for b in boqs if b.status == "Approved"), None)
	if approved:
		return approved.name
	live = next((b for b in boqs if b.status != "Superseded"), None)
	return (live or boqs[0]).name


@frappe.whitelist()
def create_boq_revision(name: str):
	"""Raise a Draft BOQ revision from an Approved change order and link it back."""
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	if doc.status != "Approved":
		frappe.throw(_("A BOQ revision can only be raised from an Approved change order."))
	if doc.boq_revision:
		frappe.throw(_("A BOQ revision was already raised from this change order."))

	source = _project_source_boq(doc.project)
	if not source:
		frappe.throw(_("This project has no BOQ to revise yet."))

	from buildsuite_core.api.boq import create_revision

	new_boq = create_revision(source, source_sco=doc.name, title=f"Revision from {doc.name}")
	doc.boq_revision = new_boq
	doc.save()
	return {"boq": new_boq}
