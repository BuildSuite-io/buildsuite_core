# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Whitelisted helper to create a Customer inline from the New Project form's
client picker. The Vue form calls this so a PM doesn't have to leave the page to
add a missing customer. Gated on Project create permission — the same users who
can create a project can add a customer for it.
"""

import frappe
from frappe import _

_CUSTOMER_TYPES = ("Company", "Individual", "Partnership")


@frappe.whitelist()
def create_customer(customer_name: str, customer_type: str = "Company"):
	customer_name = (customer_name or "").strip()
	if not customer_name:
		frappe.throw(_("Customer name is required."))

	if not frappe.has_permission("Project", "create"):
		frappe.throw(_("You are not permitted to create a customer."), frappe.PermissionError)

	if customer_type not in _CUSTOMER_TYPES:
		customer_type = "Company"

	if frappe.db.exists("Customer", {"customer_name": customer_name}):
		frappe.throw(_("A customer named {0} already exists.").format(customer_name))

	doc = frappe.new_doc("Customer")
	doc.customer_name = customer_name
	doc.customer_type = customer_type

	# ERPNext makes customer_group + territory mandatory — fall back to the
	# site defaults / first non-group value so the inline create doesn't 417.
	if doc.meta.has_field("customer_group") and not doc.customer_group:
		doc.customer_group = frappe.db.get_default("customer_group") or frappe.db.get_value(
			"Customer Group", {"is_group": 0}, "name"
		)
	if doc.meta.has_field("territory") and not doc.territory:
		doc.territory = frappe.db.get_default("territory") or frappe.db.get_value(
			"Territory", {"is_group": 0}, "name"
		)

	doc.insert(ignore_permissions=True)
	return {"name": doc.name, "customer_name": doc.customer_name}
