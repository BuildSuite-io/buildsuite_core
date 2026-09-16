# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Scope Change Order approval flow (approve / reject /
revise) and the BOQ-revision tie-in raised from an approved change order. Reads +
plain CRUD go through the standard data adapter; only these transitions need the API."""

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow

from buildsuite_core.permissions.setup import BOQ_APPROVE_ROLES

SCO = "Scope Change Order"

# Approve / Reject / Revise now run through the "Scope Change Order Approval" Frappe Workflow
# (bound to the `status` field). These endpoints stay as the SPA's entry points: they keep the
# explicit role/state guards (for clear error messages + the Site-Engineer PermissionError the
# matrix relies on) and then drive the transition through Frappe's engine, which re-checks the
# transition's role/self-approval rules. The field stamping + audit-trail row are applied by the
# controller's before_save on the state change, so they fire on every path.


def _require_approver():
	if not set(frappe.get_roles()) & set(BOQ_APPROVE_ROLES):
		frappe.throw(_("You are not permitted to approve or reject a scope change order."), frappe.PermissionError)


@frappe.whitelist()
def approve_sco(name: str):
	"""Pending Approval -> Approved (via workflow). Controller stamps the approver + date."""
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	_require_approver()
	if doc.status != "Pending Approval":
		frappe.throw(_("Only a Pending Approval change order can be approved."))
	apply_workflow(frappe.as_json(doc.as_dict()), "Approve")
	return frappe.db.get_value(SCO, name, "status")


@frappe.whitelist()
def reject_sco(name: str, reason: str = None):
	"""Pending Approval -> Rejected (via workflow), recording the rejection reason."""
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("A rejection reason is required."))
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	_require_approver()
	if doc.status != "Pending Approval":
		frappe.throw(_("Only a Pending Approval change order can be rejected."))
	# apply_workflow reloads the doc from the DB, so an in-memory field set would be discarded.
	# Persist the reason first; the reload picks it up and the controller logs it on the row.
	frappe.db.set_value(SCO, name, "rejection_reason", reason)
	doc = frappe.get_doc(SCO, name)
	apply_workflow(frappe.as_json(doc.as_dict()), "Reject")
	return frappe.db.get_value(SCO, name, "status")


@frappe.whitelist()
def revise_sco(name: str):
	"""Approved / Rejected -> Pending Approval (via workflow), so it can be edited and re-submitted."""
	doc = frappe.get_doc(SCO, name)
	doc.check_permission("write")
	if doc.status not in ("Approved", "Rejected"):
		frappe.throw(_("Only an Approved or Rejected change order can be revised."))
	apply_workflow(frappe.as_json(doc.as_dict()), "Revise")
	return frappe.db.get_value(SCO, name, "status")


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
