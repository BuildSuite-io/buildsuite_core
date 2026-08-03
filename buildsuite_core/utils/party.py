# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Shared helpers for the Project Finance party masters (Customer / Supplier).

A party's contact person / phone / email live on a native ERPNext **Contact**
(linked via Dynamic Link), not on the party doc itself — so both masters read and
upsert a single primary Contact through here. Unallocated advance (advance held for
a customer, advance paid to a supplier) is the sum of that party's submitted Payment
Entries' `unallocated_amount`."""

import frappe
from frappe.utils import flt

PE = "Payment Entry"


def primary_contact(doctype, name):
	"""The party's primary/first linked Contact as {contact_person, phone, email}."""
	rows = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", doctype],
			["Dynamic Link", "link_name", "=", name],
		],
		fields=["name", "first_name", "mobile_no", "phone", "email_id"],
		order_by="creation asc",
		limit=1,
	)
	if not rows:
		return {"contact_person": "", "phone": "", "email": ""}
	c = rows[0]
	return {
		"contact_person": c.first_name or "",
		"phone": c.mobile_no or c.phone or "",
		"email": c.email_id or "",
		"_name": c.name,
	}


def upsert_primary_contact(doctype, name, party_display, contact_person, phone, email):
	"""Create or update the party's primary Contact. No-op when nothing was supplied."""
	contact_person = (contact_person or "").strip()
	phone = (phone or "").strip()
	email = (email or "").strip()
	if not (contact_person or phone or email):
		return

	existing = primary_contact(doctype, name)
	doc = frappe.get_doc("Contact", existing["_name"]) if existing.get("_name") else frappe.new_doc("Contact")
	doc.first_name = contact_person or party_display
	if doc.is_new():
		doc.append("links", {"link_doctype": doctype, "link_name": name})

	# Phone / email live in child tables; reset the primary and re-add so edits stick.
	if phone:
		doc.set("phone_nos", [])
		doc.add_phone(phone, is_primary_mobile_no=1, is_primary_phone=1)
	if email:
		doc.set("email_ids", [])
		doc.add_email(email, is_primary=1)

	doc.flags.ignore_permissions = True
	doc.save()


def unallocated_advance(party_type, party, company=None):
	"""Sum of submitted Payment Entry `unallocated_amount` for the party (its open advance)."""
	from frappe.query_builder.functions import Sum

	pe = frappe.qb.DocType(PE)
	q = (
		frappe.qb.from_(pe)
		.select(Sum(pe.unallocated_amount))
		.where((pe.docstatus == 1) & (pe.party_type == party_type) & (pe.party == party))
	)
	if company:
		q = q.where(pe.company == company)
	return flt(q.run()[0][0])
