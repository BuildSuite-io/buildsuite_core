# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Customers master, plus the inline create used by the New
Project form's client picker. Customers are native ERPNext Customers; contact
person / phone / email live on a linked Contact (see utils.party). "Advance held"
is the customer's unallocated Payment Entry balance."""

import frappe
from frappe import _

from buildsuite_core.utils.party import (
	primary_contact,
	unallocated_advance,
	upsert_primary_contact,
)

_CUSTOMER_TYPES = ("Company", "Individual", "Partnership")


def _default_group_and_territory(doc):
	"""ERPNext makes customer_group + territory mandatory — fall back to site
	defaults / first non-group value so a lean inline create doesn't 417."""
	if doc.meta.has_field("customer_group") and not doc.customer_group:
		doc.customer_group = frappe.db.get_default("customer_group") or frappe.db.get_value(
			"Customer Group", {"is_group": 0}, "name"
		)
	if doc.meta.has_field("territory") and not doc.territory:
		doc.territory = frappe.db.get_default("territory") or frappe.db.get_value(
			"Territory", {"is_group": 0}, "name"
		)


@frappe.whitelist()
def list_customers():
	"""All customers with type, tax id, primary contact and advance held, name-sorted."""
	rows = frappe.get_all(
		"Customer",
		fields=["name", "customer_name", "customer_type", "tax_id"],
		order_by="customer_name asc",
	)
	out = []
	for c in rows:
		contact = primary_contact("Customer", c.name)
		out.append(
			{
				"id": c.name,
				"name": c.customer_name,
				"type": c.customer_type or "",
				"gstin": c.tax_id or "",
				"contactPerson": contact["contact_person"],
				"phone": contact["phone"],
				"email": contact["email"],
				"advance": unallocated_advance("Customer", c.name),
			}
		)
	return out


@frappe.whitelist()
def create_customer(
	customer_name: str,
	customer_type: str = "Company",
	gstin=None,
	contact_person=None,
	phone=None,
	email=None,
):
	"""Create a Customer. Accepts the New Project picker's minimal call and the
	Customers master's fuller payload (contact person / phone / email / tax id)."""
	customer_name = (customer_name or "").strip()
	if not customer_name:
		frappe.throw(_("Customer name is required."))

	if not frappe.has_permission("Customer", "create") and not frappe.has_permission("Project", "create"):
		frappe.throw(_("You are not permitted to create a customer."), frappe.PermissionError)

	if customer_type not in _CUSTOMER_TYPES:
		customer_type = "Company"

	if frappe.db.exists("Customer", {"customer_name": customer_name}):
		frappe.throw(_("A customer named {0} already exists.").format(customer_name))

	doc = frappe.new_doc("Customer")
	doc.customer_name = customer_name
	doc.customer_type = customer_type
	doc.tax_id = (gstin or "").strip() or None
	_default_group_and_territory(doc)
	doc.insert(ignore_permissions=True)

	upsert_primary_contact("Customer", doc.name, doc.customer_name, contact_person, phone, email)
	return {"name": doc.name, "customer_name": doc.customer_name}


@frappe.whitelist()
def update_customer(
	name: str,
	new_name=None,
	customer_type=None,
	gstin=None,
	contact_person=None,
	phone=None,
	email=None,
):
	"""Update a customer's name / type / tax id and its primary contact."""
	if not frappe.has_permission("Customer", "write"):
		frappe.throw(_("You are not permitted to edit a customer."), frappe.PermissionError)

	doc = frappe.get_doc("Customer", name)
	new_name = (new_name or "").strip()
	if new_name and new_name != doc.customer_name:
		if frappe.db.exists("Customer", {"customer_name": new_name, "name": ["!=", name]}):
			frappe.throw(_("A customer named {0} already exists.").format(new_name))
		doc.customer_name = new_name

	if customer_type in _CUSTOMER_TYPES:
		doc.customer_type = customer_type
	if gstin is not None:
		doc.tax_id = gstin.strip() or None
	doc.save(ignore_permissions=True)

	upsert_primary_contact("Customer", doc.name, doc.customer_name, contact_person, phone, email)
	return {"name": doc.name, "customer_name": doc.customer_name}
