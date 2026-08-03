# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Finance › Suppliers master. Subcontractors ARE suppliers (ERPNext
model) of type "Subcontractor" — this master lists both, so the Vue panel shows a
single unified list where subcontractor rows route into the Subcontract module and
regular suppliers are created / edited here. Contact person / phone / email live on
a linked Contact (see utils.party); "advance paid" is the supplier's unallocated
Payment Entry balance."""

import frappe
from frappe import _

from buildsuite_core.utils.party import (
	primary_contact,
	unallocated_advance,
	upsert_primary_contact,
)

# Regular-supplier types (the modal's options). "Subcontractor" is reserved for the
# Subcontract module's master, so it is not offered here.
_SUPPLIER_TYPES = ("Company", "Individual", "Partnership")


def _default_supplier_group(subcontractor=False):
	if subcontractor:
		return "Subcontractor"
	return (
		frappe.db.get_default("supplier_group")
		or frappe.db.get_value("Supplier Group", {"is_group": 0, "name": ["!=", "Subcontractor"]}, "name")
		or frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	)


@frappe.whitelist()
def list_suppliers():
	"""Every supplier (incl. subcontractors) with type, trade, tax id, primary contact
	and advance paid — name-sorted. Subcontractor rows carry is_subcontractor + trade."""
	rows = frappe.get_all(
		"Supplier",
		fields=["name", "supplier_name", "supplier_type", "tax_id", "custom_trade"],
		order_by="supplier_name asc",
	)
	out = []
	for s in rows:
		is_sub = s.supplier_type == "Subcontractor"
		contact = primary_contact("Supplier", s.name)
		out.append(
			{
				"id": s.name,
				"name": s.supplier_name,
				"type": s.supplier_type or "",
				"is_subcontractor": is_sub,
				"trade": s.custom_trade or "" if is_sub else "",
				"gstin": s.tax_id or "",
				"contactPerson": contact["contact_person"],
				"phone": contact["phone"],
				"email": contact["email"],
				"advance": unallocated_advance("Supplier", s.name),
			}
		)
	return out


@frappe.whitelist()
def create_supplier(
	supplier_name: str,
	supplier_type: str = "Company",
	gstin=None,
	contact_person=None,
	phone=None,
	email=None,
):
	"""Create a regular Supplier (subcontractors are created in the Subcontract module)."""
	supplier_name = (supplier_name or "").strip()
	if not supplier_name:
		frappe.throw(_("Supplier name is required."))
	if not frappe.has_permission("Supplier", "create"):
		frappe.throw(_("You are not permitted to create a supplier."), frappe.PermissionError)

	if supplier_type not in _SUPPLIER_TYPES:
		supplier_type = "Company"
	if frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
		frappe.throw(_("A supplier named {0} already exists.").format(supplier_name))

	doc = frappe.new_doc("Supplier")
	doc.supplier_name = supplier_name
	doc.supplier_type = supplier_type
	doc.supplier_group = _default_supplier_group()
	doc.tax_id = (gstin or "").strip() or None
	doc.insert(ignore_permissions=True)

	upsert_primary_contact("Supplier", doc.name, doc.supplier_name, contact_person, phone, email)
	return {"name": doc.name, "supplier_name": doc.supplier_name}


@frappe.whitelist()
def update_supplier(
	name: str,
	new_name=None,
	supplier_type=None,
	gstin=None,
	contact_person=None,
	phone=None,
	email=None,
):
	"""Update a supplier's name / type / tax id and its primary contact. Subcontractors
	are managed in the Subcontract module, not here."""
	if not frappe.has_permission("Supplier", "write"):
		frappe.throw(_("You are not permitted to edit a supplier."), frappe.PermissionError)

	doc = frappe.get_doc("Supplier", name)
	if doc.supplier_type == "Subcontractor":
		frappe.throw(_("Subcontractors are managed in the Subcontract module."))

	new_name = (new_name or "").strip()
	if new_name and new_name != doc.supplier_name:
		if frappe.db.exists("Supplier", {"supplier_name": new_name, "name": ["!=", name]}):
			frappe.throw(_("A supplier named {0} already exists.").format(new_name))
		doc.supplier_name = new_name

	if supplier_type in _SUPPLIER_TYPES:
		doc.supplier_type = supplier_type
	if gstin is not None:
		doc.tax_id = gstin.strip() or None
	doc.save(ignore_permissions=True)

	upsert_primary_contact("Supplier", doc.name, doc.supplier_name, contact_person, phone, email)
	return {"name": doc.name, "supplier_name": doc.supplier_name}
