# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Sales > Leads — the status rules and mobile matching shared by the Lead / Quotation hooks and
the leads API.

A lead's status is partly typed and partly derived:

- By hand: Lead → Open → Interested, and Do Not Contact at any time (stopping is a decision).
- From its quotations: Quotation while any is live, Lost Quotation once every one is lost or
  expired, back to Open when the last one goes.
- Converted: once a Customer carries the lead (Customer.lead_name) — ERPNext sets it.

ERPNext derives the same statuses, but only from SUBMITTED quotations (Lead.has_quotation looks
at docstatus 1), and BuildSuite quotations are drafts. Left alone, ERPNext's own set_status would
put a draft-quoted lead back to Open on every save. So the Lead validate hook re-applies the rule
after ERPNext's, and the Quotation hooks re-sync a lead whenever one of its quotations changes.
"""

import re

import frappe

MANUAL_STATUSES = ("Lead", "Open", "Interested")
DO_NOT_CONTACT = "Do Not Contact"
CONVERTED = "Converted"
# Set by the system only: the lead's quotations, and its conversion to a customer.
SYSTEM_STATUSES = ("Quotation", "Lost Quotation", CONVERTED)
# A quotation in one of these is over; anything else (Draft, Open, Replied, Ordered…) is live.
_ENDED_QUOTATION_STATUSES = ("Lost", "Expired")


def mobile_key(value):
	"""The last ten digits of a phone number, so `+91 98471 20101`, `098471-20101` and
	`9847120101` are the same person. Fewer than ten digits is no key at all."""
	digits = re.sub(r"\D", "", value or "")
	return digits[-10:] if len(digits) >= 10 else ""


def converted_customer(lead):
	"""The Customer this lead became (Customer.lead_name — ERPNext's own link), or None."""
	return frappe.db.get_value("Customer", {"lead_name": lead}, "name") if lead else None


def quotation_statuses(lead, exclude=None):
	"""Statuses of the lead's quotations that are not cancelled."""
	filters = {"quotation_to": "Lead", "party_name": lead, "docstatus": ["<", 2]}
	if exclude:
		filters["name"] = ["!=", exclude]
	return frappe.get_all("Quotation", filters=filters, pluck="status")


def status_from_quotations(lead, current, exclude=None):
	"""What the lead's quotations say its status is, or None when they have no say."""
	statuses = quotation_statuses(lead, exclude=exclude)
	if statuses:
		if any(s not in _ENDED_QUOTATION_STATUSES for s in statuses):
			return "Quotation"
		return "Lost Quotation"
	# Its last quotation is gone: a quotation status no longer means anything.
	if current in ("Quotation", "Lost Quotation", "Opportunity"):
		return "Open"
	return None


def apply_quotation_status(doc, method=None):
	"""Lead validate hook — runs after ERPNext's own Lead.validate/set_status."""
	if doc.is_new():
		# A new lead starts by hand; only Do Not Contact or a manual stage can be typed in.
		if doc.status not in (*MANUAL_STATUSES, DO_NOT_CONTACT):
			doc.status = "Lead"
		return
	if doc.status in (CONVERTED, DO_NOT_CONTACT):
		return
	if converted_customer(doc.name):
		doc.status = CONVERTED
		return
	status = status_from_quotations(doc.name, doc.status)
	if status:
		doc.status = status


def sync_lead_status(lead, exclude_quotation=None):
	"""Re-derive a saved lead's status after one of its quotations changed."""
	if not lead or not frappe.db.exists("Lead", lead):
		return
	current = frappe.db.get_value("Lead", lead, "status")
	if current in (CONVERTED, DO_NOT_CONTACT):
		return
	if converted_customer(lead):
		new = CONVERTED
	else:
		new = status_from_quotations(lead, current, exclude=exclude_quotation) or current
	if new != current:
		frappe.db.set_value("Lead", lead, "status", new, update_modified=False)


def _leads_of(doc):
	leads = set()
	if doc.get("quotation_to") == "Lead" and doc.get("party_name"):
		leads.add(doc.party_name)
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	if before and before.get("quotation_to") == "Lead" and before.get("party_name"):
		# A draft moved to someone else: the lead it left needs re-syncing too.
		leads.add(before.party_name)
	return leads


def sync_quotation_leads(doc, method=None):
	"""Quotation after_insert / on_update / on_submit / on_cancel hook."""
	for lead in _leads_of(doc):
		sync_lead_status(lead)


def sync_quotation_leads_on_delete(doc, method=None):
	"""Quotation on_trash hook — the row is still there, so leave it out of the count."""
	if doc.get("quotation_to") == "Lead" and doc.get("party_name"):
		sync_lead_status(doc.party_name, exclude_quotation=doc.name)


def mobile_matches(mobile, except_lead=None):
	"""Leads and customers already on file with this mobile number.

	A warning, never a block: the same person asking twice is common, and so is a shared family
	number. Customers are matched on their own mobile and on their contacts' phone numbers (a
	BuildSuite customer keeps its phone on the primary Contact)."""
	key = mobile_key(mobile)
	if not key:
		return []
	digits = "right(regexp_replace({0}, '[^0-9]', ''), 10)"
	out = []
	leads = frappe.db.sql(
		f"""select name, lead_name, company_name, status from `tabLead`
		where {digits.format("mobile_no")} = %(key)s and name != %(except)s
		order by creation desc limit 5""",
		{"key": key, "except": except_lead or ""},
		as_dict=True,
	)
	for lead in leads:
		out.append(
			{
				"kind": "Lead",
				"id": lead.name,
				"name": lead.company_name or lead.lead_name or lead.name,
				"status": lead.status,
			}
		)
	customers = frappe.db.sql(
		f"""select distinct c.name, c.customer_name from `tabCustomer` c
		left join `tabDynamic Link` dl on dl.link_doctype = 'Customer' and dl.link_name = c.name
			and dl.parenttype = 'Contact'
		left join `tabContact Phone` cp on cp.parent = dl.parent
		where c.disabled = 0
			and (%(except)s = '' or ifnull(c.lead_name, '') != %(except)s)
			and ({digits.format("c.mobile_no")} = %(key)s or {digits.format("cp.phone")} = %(key)s)
		limit 5""",
		# The lead's own customer (once converted) is not a duplicate of it.
		{"key": key, "except": except_lead or ""},
		as_dict=True,
	)
	for c in customers:
		out.append({"kind": "Customer", "id": c.name, "name": c.customer_name or c.name, "status": ""})
	return out
