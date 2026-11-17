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
	out = []
	# The last ten digits of a stored number, compared with the key (see mobile_key).
	leads = frappe.db.sql(
		"""select name, lead_name, company_name, status from `tabLead`
		where right(regexp_replace(mobile_no, '[^0-9]', ''), 10) = %(key)s and name != %(except)s
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
		"""select distinct c.name, c.customer_name from `tabCustomer` c
		left join `tabDynamic Link` dl on dl.link_doctype = 'Customer' and dl.link_name = c.name
			and dl.parenttype = 'Contact'
		left join `tabContact Phone` cp on cp.parent = dl.parent
		where c.disabled = 0
			and (%(except)s = '' or ifnull(c.lead_name, '') != %(except)s)
			and (right(regexp_replace(c.mobile_no, '[^0-9]', ''), 10) = %(key)s
				or right(regexp_replace(cp.phone, '[^0-9]', ''), 10) = %(key)s)
		limit 5""",
		# The lead's own customer (once converted) is not a duplicate of it.
		{"key": key, "except": except_lead or ""},
		as_dict=True,
	)
	for c in customers:
		out.append({"kind": "Customer", "id": c.name, "name": c.customer_name or c.name, "status": ""})
	return out


def _customer_with_mobile(mobile):
	"""An existing customer (not already some lead's) with the same mobile, to link instead."""
	for match in mobile_matches(mobile):
		if match["kind"] == "Customer" and not frappe.db.get_value("Customer", match["id"], "lead_name"):
			return match["id"]
	return None


def _require_enabled(lead):
	"""A disabled lead is not converted. Some ERPNext versions ship validate_lead_is_enabled for
	this and others (16.50) do not, so the check is made here either way."""
	try:
		from erpnext.crm.doctype.lead.lead import validate_lead_is_enabled
	except ImportError:
		validate_lead_is_enabled = None
	if validate_lead_is_enabled:
		validate_lead_is_enabled(lead, "Customer")
	elif frappe.db.get_value("Lead", lead, "disabled"):
		frappe.throw(frappe._("Lead {0} is disabled, so it can't be converted to a customer.").format(lead))


def convert_lead_to_customer(lead):
	"""Make the lead a customer, or link the customer already on file with the same mobile.
	ERPNext marks the lead Converted and moves its quotations to the customer either way.

	Returns (customer, linked, existing): `linked` when an existing customer was linked rather
	than a new one made, `existing` when the lead had been converted already. The caller checks
	the user may convert (write on the lead, create on Customer)."""
	from erpnext.crm.doctype.lead.lead import _make_customer

	from buildsuite_core.api.customers import _default_group_and_territory
	from buildsuite_core.utils.session import as_administrator

	if existing := converted_customer(lead):
		return existing, False, True

	_require_enabled(lead)
	mobile = frappe.db.get_value("Lead", lead, "mobile_no")
	# Elevated for the plumbing only: ERPNext re-points the lead's quotations to the customer
	# only where the session user can write them, and links the lead's Contact and Address.
	with as_administrator():
		if match := _customer_with_mobile(mobile):
			customer = frappe.get_doc("Customer", match)
			customer.lead_name = lead
			customer.save(ignore_permissions=True)
			# Customer.on_update only follows a lead set on a NEW customer; do what it would.
			customer.update_lead_status()
			linked = True
		else:
			customer = _make_customer(lead, ignore_permissions=True)
			_default_group_and_territory(customer)
			customer.insert(ignore_permissions=True)
			linked = False
	_move_quotations_to_customer(lead, customer)
	return customer.name, linked, False


def _move_quotations_to_customer(lead, customer):
	"""Re-point the lead's quotations (drafts and sent ones; not cancelled) to the customer, so the
	project and invoices that follow have one. Older ERPNext did this on conversion; 16.50 only
	marks the lead Converted. Written straight to the rows, as ERPNext did — a sent quotation is
	submitted and could not be saved — and harmless where a version already moved them."""
	for name in frappe.get_all(
		"Quotation",
		filters={"quotation_to": "Lead", "party_name": lead, "docstatus": ["<", 2]},
		pluck="name",
	):
		frappe.db.set_value(
			"Quotation",
			name,
			{
				"quotation_to": "Customer",
				"party_name": customer.name,
				"customer_name": customer.customer_name,
			},
		)
