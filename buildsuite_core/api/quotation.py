# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Quotation lifecycle: send, accept, reject.

A quotation is a draft until it is sent (ERPNext submit -> "Open"). The client then accepts it or
turns it down. Accepting converts the lead it went to into a customer, which is what the project
and the invoices are raised against. Rejecting is ERPNext's "Set as Lost" and asks why.

The SPA's labels (Sent / Accepted / Rejected) are display names for ERPNext's own statuses; see
utils.quotation.offer_status. Nothing here changes what `status` holds.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today

from buildsuite_core.utils.lead import convert_lead_to_customer
from buildsuite_core.utils.quotation import offer_status


def _names(value):
	"""A JSON list (or list) of master names, blanks dropped."""
	if isinstance(value, str):
		value = frappe.parse_json(value) if value.strip() else []
	return [v for v in (value or []) if v]


def _quotation(name, ptype):
	doc = frappe.get_doc("Quotation", name)
	doc.check_permission(ptype)
	return doc


@frappe.whitelist()
def send_quotation(name: str):
	"""Submit the draft: it is out to the client now."""
	doc = _quotation(name, "submit")
	if doc.docstatus != 0:
		frappe.throw(_("Only a draft quotation can be sent."))
	doc.submit()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def accept_quotation(name: str):
	"""The client accepted. A quotation to a lead converts the lead; the quotation then names
	the customer, so the project and invoices have one, if the user may create customers (else the lead waits)."""
	doc = _quotation(name, "write")
	if doc.docstatus != 1 or doc.status not in ("Open", "Replied"):
		frappe.throw(_("Only a sent quotation that is still open can be accepted."))
	if doc.accepted_on:
		frappe.throw(_("This quotation was already accepted."))
	customer = None
	linked = False
	# Whoever raises quotations (Estimator, QS) may not be allowed to create customers. Their
	# acceptance still counts; the lead waits for someone who can convert it, and a project
	# cannot be made from the quotation until then (api.boq._customer_of_won_quotation).
	if doc.quotation_to == "Lead" and frappe.has_permission("Customer", "create"):
		customer, linked, _existing = convert_lead_to_customer(doc.party_name)
	doc.db_set("accepted_on", now_datetime())
	doc.add_comment("Comment", _("Accepted by the client."))
	return {"name": doc.name, "customer": customer, "linked": linked}


@frappe.whitelist()
def reject_quotation(
	name: str,
	lost_reasons: str | list | None = None,
	competitors: str | list | None = None,
	detailed_reason: str | None = None,
):
	"""The client turned it down: ERPNext's "Set as Lost", which needs at least one reason."""
	doc = _quotation(name, "write")
	if doc.docstatus != 1 or doc.status not in ("Open", "Replied"):
		frappe.throw(_("Only a sent quotation that is still open can be rejected."))
	if doc.accepted_on:
		frappe.throw(_("An accepted quotation cannot be rejected."))
	reasons = [{"lost_reason": r} for r in _names(lost_reasons)]
	if not reasons and not (detailed_reason or "").strip():
		frappe.throw(_("Say why the quotation was lost."))
	doc.declare_enquiry_lost(reasons, [{"competitor": c} for c in _names(competitors)], detailed_reason)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def quotation_kpis():
	"""The Quotations list's figures, over the quotations the user can read, in company currency:
	- awaiting_value: sent and not answered yet;
	- won_value: accepted;
	- win_rate: accepted out of those decided (accepted or rejected), None when nothing is decided;
	- past_validity: sent and past their valid-till date (ERPNext's daily job marks them Expired)."""
	rows = frappe.get_list(
		"Quotation",
		fields=["docstatus", "status", "accepted_on", "valid_till", "base_grand_total"],
		limit_page_length=0,
	)
	now = getdate(today())
	by_status = {}
	past_validity = 0
	for r in rows:
		label = offer_status(r.docstatus, r.status, r.accepted_on)
		by_status.setdefault(label, []).append(r)
		if label == "Expired" or (label == "Sent" and r.valid_till and getdate(r.valid_till) < now):
			past_validity += 1
	accepted = len(by_status.get("Accepted", []))
	decided = accepted + len(by_status.get("Rejected", []))
	return {
		"awaiting_value": sum(flt(r.base_grand_total) for r in by_status.get("Sent", [])),
		"won_value": sum(flt(r.base_grand_total) for r in by_status.get("Accepted", [])),
		"win_rate": round(accepted * 100 / decided) if decided else None,
		"past_validity": past_validity,
	}
