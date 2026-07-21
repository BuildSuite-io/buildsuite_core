# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Migrate the bespoke `Subcontractor` doctype into native `Supplier` records
(supplier_type = "Subcontractor"), repoint the Work Order / Bill foreign keys, then retire
the doctype.

Runs in pre_model_sync so the FK columns still point at Subcontractor names while we rewrite
them to Supplier names — by the time model-sync flips `subcontractor` options to Supplier, the
values are already valid. Idempotent: a no-op once `tabSubcontractor` is gone.

Because after_migrate (which installs our custom fields + property setters) hasn't run yet at
this point, we apply the Supplier extensions we depend on up front."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

SUPPLIER_TYPE = "Subcontractor"
SUPPLIER_GROUP = "Subcontractor"


def execute():
	if not frappe.db.table_exists("Subcontractor"):
		return

	_ensure_supplier_extensions()
	_ensure_supplier_group()

	name_map = {}  # old Subcontractor name -> Supplier name
	for sub in frappe.get_all(
		"Subcontractor",
		fields=[
			"name",
			"subcontractor_name",
			"trade",
			"status",
			"supplier",
			"tax_id",
			"secondary_tax_id",
			"contact_person",
			"phone",
			"email",
		],
	):
		supplier_name = _resolve_supplier(sub)
		name_map[sub.name] = supplier_name
		if sub.secondary_tax_id:
			print(
				f"  [migrate] dropped secondary_tax_id {sub.secondary_tax_id!r} from {sub.name} "
				"(slim migration — not carried to Supplier)"
			)

	_repoint("Subcontractor Work Order", name_map)
	_repoint("Subcontractor Bill", name_map)

	# Retire the doctype + table.
	frappe.delete_doc("DocType", "Subcontractor", force=True, ignore_permissions=True)
	frappe.db.sql_ddl("drop table if exists `tabSubcontractor`")


def _ensure_supplier_extensions():
	make_property_setter(
		"Supplier",
		"supplier_type",
		"options",
		"Company\nIndividual\nPartnership\nSubcontractor",
		"Text",
		validate_fields_for_doctype=False,
	)
	create_custom_fields(
		{
			"Supplier": [
				{
					"fieldname": "custom_trade",
					"fieldtype": "Link",
					"label": "Trade",
					"options": "Construction Trade",
					"insert_after": "supplier_type",
					"depends_on": "eval:doc.supplier_type=='Subcontractor'",
					"module": "BuildSuite Core",
				}
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="Supplier")


def _ensure_supplier_group():
	if frappe.db.exists("Supplier Group", SUPPLIER_GROUP):
		return
	parent = frappe.db.get_value("Supplier Group", {"is_group": 1}, "name") or "All Supplier Groups"
	frappe.get_doc(
		{"doctype": "Supplier Group", "supplier_group_name": SUPPLIER_GROUP, "parent_supplier_group": parent}
	).insert(ignore_permissions=True)


def _resolve_supplier(sub):
	"""Return the Supplier name for a Subcontractor — its linked supplier, an existing
	same-named supplier, or a freshly created one — updated with the subcontractor's attrs."""
	target = None
	if sub.supplier and frappe.db.exists("Supplier", sub.supplier):
		target = sub.supplier
	elif frappe.db.exists("Supplier", sub.subcontractor_name):
		target = sub.subcontractor_name

	if target:
		doc = frappe.get_doc("Supplier", target)
	else:
		doc = frappe.new_doc("Supplier")
		doc.supplier_name = sub.subcontractor_name

	doc.supplier_type = SUPPLIER_TYPE
	if not doc.supplier_group:
		doc.supplier_group = SUPPLIER_GROUP
	doc.custom_trade = sub.trade
	if sub.tax_id and not doc.tax_id:
		doc.tax_id = sub.tax_id
	doc.disabled = 1 if sub.status == "Inactive" else 0
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save() if target else doc.insert()

	_ensure_contact(doc.name, sub)
	return doc.name


def _ensure_contact(supplier, sub):
	"""Preserve the subcontractor's contact person/phone/email as a native Contact linked to
	the Supplier (slim migration — contact info lives on the native Contact, not the Supplier)."""
	if not (sub.contact_person or sub.phone or sub.email):
		return
	first_name = sub.contact_person or sub.subcontractor_name
	exists = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", supplier],
			["Contact", "first_name", "=", first_name],
		],
		limit=1,
	)
	if exists:
		return
	contact = frappe.new_doc("Contact")
	contact.first_name = first_name
	if sub.phone:
		contact.append("phone_nos", {"phone": sub.phone, "is_primary_phone": 1})
	if sub.email:
		contact.append("email_ids", {"email_id": sub.email, "is_primary": 1})
	contact.append("links", {"link_doctype": "Supplier", "link_name": supplier})
	contact.flags.ignore_permissions = True
	contact.flags.ignore_mandatory = True
	contact.insert()


def _repoint(doctype, name_map):
	table = f"tab{doctype}"
	if not frappe.db.table_exists(doctype):
		return
	for old, new in name_map.items():
		if old == new:
			continue
		supplier_name = frappe.db.get_value("Supplier", new, "supplier_name")
		frappe.db.sql(
			f"update `{table}` set subcontractor = %s, subcontractor_name = %s where subcontractor = %s",
			(new, supplier_name, old),
		)
