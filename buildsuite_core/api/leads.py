# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Sales > Leads — enquiries that are not customers yet, on ERPNext's own Lead doctype.

A lead is the person (or business) who asked for a price. Quotations can go to a lead; once one
is won the lead is converted, which makes an ERPNext Customer that carries the lead
(Customer.lead_name). ERPNext then marks the lead Converted and re-points the lead's quotations
to the customer, so the project and the invoices that follow have a real customer.

The status rules live in utils.lead; this module is the SPA's read/write surface.
"""

import frappe
from frappe import _
from frappe.utils import cstr

from buildsuite_core.utils.lead import (
	CONVERTED,
	DO_NOT_CONTACT,
	MANUAL_STATUSES,
	SYSTEM_STATUSES,
	convert_lead_to_customer,
	converted_customer,
	mobile_matches,
)
from buildsuite_core.utils.project import company_scope, default_company

# The fields the SPA edits, by their ERPNext names. `utm_source` is the Lead's Source in v16.
_EDITABLE = (
	"first_name",
	"last_name",
	"company_name",
	"mobile_no",
	"email_id",
	"city",
	"state",
	"utm_source",
	"lead_owner",
	"enquiry_note",
)
_LIST_FIELDS = (
	"name",
	"lead_name",
	"first_name",
	"last_name",
	"company_name",
	"mobile_no",
	"email_id",
	"city",
	"state",
	"utm_source",
	"status",
	"lead_owner",
	"creation",
)


def _clean(value):
	return cstr(value).strip() or None


def _party_name(lead):
	"""The name quotations and the customer carry: the organisation, else the person."""
	return lead.get("company_name") or lead.get("lead_name") or lead.get("name")


def _quotations_by_party(party_type, names):
	"""{party: [quotation rows, newest first]} for the given leads or customers."""
	if not names:
		return {}
	rows = frappe.get_all(
		"Quotation",
		filters={"quotation_to": party_type, "party_name": ["in", list(names)], "docstatus": ["<", 2]},
		fields=["name", "party_name", "title", "status", "grand_total", "currency", "transaction_date"],
		order_by="transaction_date desc, creation desc",
	)
	lost = _lost_reasons([r.name for r in rows if r.status == "Lost"])
	out = {}
	for r in rows:
		r["lost_reasons"] = lost.get(r.name, [])
		out.setdefault(r.party_name, []).append(r)
	return out


def _lost_reasons(quotations):
	if not quotations:
		return {}
	rows = frappe.get_all(
		"Quotation Lost Reason Detail",
		filters={"parent": ["in", quotations], "parenttype": "Quotation"},
		fields=["parent", "lost_reason"],
	)
	out = {}
	for r in rows:
		out.setdefault(r.parent, []).append(r.lost_reason)
	return out


def _customers_of(leads):
	"""{lead: {name, customer_name, customer_type, creation}} for converted leads."""
	if not leads:
		return {}
	rows = frappe.get_all(
		"Customer",
		filters={"lead_name": ["in", list(leads)]},
		fields=["name", "customer_name", "customer_type", "creation", "lead_name"],
	)
	return {r.lead_name: r for r in rows}


def _summary(quotations):
	latest = quotations[0] if quotations else None
	return {
		"quotation_count": len(quotations),
		"latest_quotation_total": latest.grand_total if latest else 0,
		"latest_quotation_currency": latest.currency if latest else None,
		"latest_quotation_status": latest.status if latest else None,
		"latest_lost_reasons": latest.lost_reasons if latest and latest.status == "Lost" else [],
	}


def _with_quotations(leads):
	"""Attach quotation and customer facts to lead rows. A converted lead's quotations were
	re-pointed to its customer by ERPNext, so for those the customer's quotations count."""
	names = [lead.name for lead in leads]
	customers = _customers_of(names)
	to_lead = _quotations_by_party("Lead", names)
	to_customer = _quotations_by_party("Customer", [c.name for c in customers.values()])
	for lead in leads:
		customer = customers.get(lead.name)
		quotations = to_customer.get(customer.name, []) if customer else to_lead.get(lead.name, [])
		lead.update(_summary(quotations))
		lead["customer"] = customer.name if customer else None
		lead["customer_name"] = customer.customer_name if customer else None
		lead["party_name"] = _party_name(lead)
	return leads


@frappe.whitelist()
def list_leads():
	"""Every lead the user can read in the working company, newest first, with its quotation
	count and latest total. Search and filters run in the browser, as the Customers list does."""
	frappe.has_permission("Lead", "read", throw=True)
	# A lead from before company awareness has no company; it shows in every company.
	or_filters = None
	if company := company_scope():
		or_filters = [["company", "=", company], ["company", "is", "not set"]]
	leads = frappe.get_list(
		"Lead",
		or_filters=or_filters,
		fields=list(_LIST_FIELDS),
		order_by="creation desc",
		limit_page_length=0,
	)
	return _with_quotations(leads)


@frappe.whitelist()
def get_lead(name: str):
	"""One lead for its page: the fields, its quotations, the customer it became (if any), other
	records on file with the same mobile, and what the user may do with it."""
	doc = frappe.get_doc("Lead", name)
	doc.check_permission("read")
	lead = frappe._dict({f: doc.get(f) for f in (*_LIST_FIELDS, *_EDITABLE)})
	customer = _customers_of([name]).get(name)
	if customer:
		quotations = _quotations_by_party("Customer", [customer.name]).get(customer.name, [])
	else:
		quotations = _quotations_by_party("Lead", [name]).get(name, [])
	lead.update(_summary(quotations))
	lead["party_name"] = _party_name(lead)
	lead["customer"] = customer.name if customer else None
	return {
		"lead": lead,
		"quotations": quotations,
		"customer": customer,
		"mobile_matches": mobile_matches(doc.mobile_no, except_lead=name),
		# ERPNext's own notes table on the lead (CRM Note): who wrote what, when. Newest first.
		"notes": _notes(doc),
		"can": {
			"write": bool(frappe.has_permission("Lead", "write", doc)),
			"delete": bool(frappe.has_permission("Lead", "delete", doc)),
			"convert": bool(
				frappe.has_permission("Lead", "write", doc) and frappe.has_permission("Customer", "create")
			),
		},
	}


@frappe.whitelist()
def find_mobile_matches(mobile: str | None = None, except_lead: str | None = None):
	"""Leads and customers already on file with this mobile — the "same person again" warning."""
	frappe.has_permission("Lead", "read", throw=True)
	return mobile_matches(mobile, except_lead=except_lead)


def _apply(doc, values):
	for field in _EDITABLE:
		if field in values:
			doc.set(field, _clean(values.get(field)))
	if doc.utm_source and not frappe.db.exists("UTM Source", doc.utm_source):
		doc.utm_source = None
	if not (doc.first_name or doc.company_name):
		frappe.throw(_("A lead needs a person's name or an organisation's name."))


@frappe.whitelist(methods=["POST"])
def create_lead(**values):
	"""Add a lead. It starts in Lead, owned by whoever adds it unless an owner is given."""
	frappe.has_permission("Lead", "create", throw=True)
	values.pop("cmd", None)
	doc = frappe.new_doc("Lead")
	_apply(doc, values)
	doc.lead_owner = doc.lead_owner or frappe.session.user
	doc.company = default_company()
	doc.status = values.get("status") if values.get("status") in MANUAL_STATUSES else "Lead"
	doc.insert()
	return {
		"name": doc.name,
		"lead_name": doc.lead_name,
		"party_name": _party_name(doc),
		"mobile_no": doc.mobile_no,
		"status": doc.status,
	}


def _check_status_change(doc, status):
	if status == doc.status:
		return
	if doc.status == CONVERTED or converted_customer(doc.name):
		frappe.throw(_("A converted lead's status is set by its customer."))
	if status in SYSTEM_STATUSES:
		frappe.throw(_("{0} is set by the system: it follows the lead's quotations.").format(_(status)))
	if status not in (*MANUAL_STATUSES, DO_NOT_CONTACT):
		frappe.throw(_("{0} is not a lead status here.").format(status))
	# With quotations, the lead follows them — except Do Not Contact, and taking a stopped lead
	# back (the quotations then decide again).
	has_quotations = frappe.db.exists(
		"Quotation", {"quotation_to": "Lead", "party_name": doc.name, "docstatus": ["<", 2]}
	)
	if has_quotations and status != DO_NOT_CONTACT and doc.status != DO_NOT_CONTACT:
		frappe.throw(_("That status is set by the lead's quotations."))


@frappe.whitelist(methods=["POST"])
def update_lead(name: str, **values):
	"""Save the lead's page. A status change is checked against the rules in utils.lead; the
	quotations then have the last word (the Lead validate hook)."""
	values.pop("cmd", None)
	doc = frappe.get_doc("Lead", name)
	doc.check_permission("write")
	_apply(doc, values)
	if values.get("status"):
		_check_status_change(doc, values["status"])
		doc.status = values["status"]
	doc.save()
	# Draft quotations still carry the old name until they are next saved; follow the rename.
	frappe.db.set_value(
		"Quotation",
		{"quotation_to": "Lead", "party_name": name, "docstatus": 0},
		"customer_name",
		_party_name(doc),
		update_modified=False,
	)
	return get_lead(name)


@frappe.whitelist(methods=["POST"])
def delete_lead(name: str):
	"""Delete a lead that has gone nowhere. One with quotations or a customer is history."""
	doc = frappe.get_doc("Lead", name)
	doc.check_permission("delete")
	if converted_customer(name):
		frappe.throw(_("This lead is a customer now, so it stays on record."))
	if frappe.db.exists("Quotation", {"quotation_to": "Lead", "party_name": name}):
		frappe.throw(_("This lead has quotations, so it stays on record."))
	frappe.delete_doc("Lead", name)
	return {"ok": True}


@frappe.whitelist(methods=["POST"])
def convert_lead(name: str):
	"""Make the lead a customer. A customer already on file with the same mobile is linked to the
	lead instead of making a second one. ERPNext marks the lead Converted and moves its
	quotations to the customer either way (utils.lead.convert_lead_to_customer)."""
	lead = frappe.get_doc("Lead", name)
	lead.check_permission("write")
	if not frappe.has_permission("Customer", "create"):
		frappe.throw(
			_(
				"Converting a lead makes a customer, which your role cannot do. Ask someone who can create customers."
			),
			frappe.PermissionError,
		)
	customer, linked, existing = convert_lead_to_customer(name)
	out = {
		"customer": customer,
		"customer_name": frappe.db.get_value("Customer", customer, "customer_name"),
		"linked": linked,
	}
	if existing:
		out["existing"] = True
	return out


# --- Notes: ERPNext's CRM Note table on the lead -------------------------------------------------


def _notes(doc):
	rows = [
		{"name": n.name, "note": n.note, "added_by": n.added_by, "added_on": n.added_on}
		for n in doc.get("notes") or []
	]
	return sorted(rows, key=lambda r: str(r["added_on"] or ""), reverse=True)


def _lead_for_notes(name):
	doc = frappe.get_doc("Lead", name)
	doc.check_permission("write")
	return doc


def _require_text(note):
	if not cstr(note).strip():
		frappe.throw(_("A note cannot be empty."))


@frappe.whitelist(methods=["POST"])
def add_note(lead: str, note: str):
	"""Add a note to the lead (ERPNext's Lead.add_note stamps who and when)."""
	_require_text(note)
	doc = _lead_for_notes(lead)
	doc.add_note(note)
	return _notes(frappe.get_doc("Lead", lead))


@frappe.whitelist(methods=["POST"])
def edit_note(lead: str, row_id: str, note: str):
	_require_text(note)
	_lead_for_notes(lead).edit_note(note, row_id)
	return _notes(frappe.get_doc("Lead", lead))


@frappe.whitelist(methods=["POST"])
def delete_note(lead: str, row_id: str):
	_lead_for_notes(lead).delete_note(row_id)
	return _notes(frappe.get_doc("Lead", lead))
