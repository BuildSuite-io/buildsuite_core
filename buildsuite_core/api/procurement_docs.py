# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted CRUD + lifecycle for the three in-app procurement documents —
Material Request, Purchase Order and Purchase Receipt. Each carries a child
`items` table that can't go through the generic data adapter, so the Vue
procurement surface reads/writes them here. All three are natively submittable:
state IS the docstatus — Draft (0) → Submitted (1) → Cancelled (2), plus Amend.

Company is anchored to the project (never the user default); a Material Request
has no parent project in ERPNext, so we treat the request as single-project and
stamp that project on every item line, deriving the request's project back from
its lines for display."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from buildsuite_core.utils.project import default_company

MATERIAL_REQUEST = "Material Request"
PURCHASE_ORDER = "Purchase Order"
PURCHASE_RECEIPT = "Purchase Receipt"

# docstatus → the lifecycle label the Vue screens show.
_DOCSTATE = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


def _state(doc):
	return _DOCSTATE.get(doc.docstatus, "Draft")


def _company_for(project=None):
	"""Company anchored to the project; fall back to the single default company."""
	if project:
		return frappe.db.get_value("Project", project, "company") or default_company()
	return default_company()


def _project_name(project):
	return frappe.db.get_value("Project", project, "project_name") if project else None


def _company_currency(company):
	return frappe.get_cached_value("Company", company, "default_currency") if company else None


# ==========================================================================
# Material Request
# ==========================================================================


def _mr_project(doc):
	"""The request's project. This app adds a mandatory parent `project` custom field
	to Material Request; fall back to a line's project for any legacy row without it."""
	if doc.get("project"):
		return doc.project
	return next((it.project for it in doc.items if it.project), None)


def _serialize_mr(doc):
	project = _mr_project(doc)
	return {
		"name": doc.name,
		"project": project,
		"project_name": _project_name(project),
		"material_request_type": doc.material_request_type,
		"transaction_date": str(doc.transaction_date) if doc.transaction_date else None,
		"schedule_date": str(doc.schedule_date) if doc.schedule_date else None,
		"requested_by": doc.owner,
		"docstatus": doc.docstatus,
		"state": _state(doc),
		"status": doc.status,
		"amended_from": doc.get("amended_from"),
		"per_ordered": flt(doc.per_ordered),
		"company": doc.company,
		"total": sum(flt(it.qty) * flt(it.rate) for it in doc.items),
		"items": [
			{
				"name": it.name,
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": it.description,
				"qty": flt(it.qty),
				"uom": it.uom,
				"rate": flt(it.rate),
				"amount": flt(it.qty) * flt(it.rate),
				"project": it.project,
				"ordered_qty": flt(it.ordered_qty),
			}
			for it in doc.items
		],
	}


def _mr_actions(doc):
	if doc.docstatus == 0:
		return ["edit", "submit", "delete"]
	if doc.docstatus == 1:
		actions = ["cancel"]
		if flt(doc.per_ordered) < 100:
			actions.insert(0, "create_po")
		return actions
	return ["amend", "delete"]


@frappe.whitelist()
def get_material_request(name):
	doc = frappe.get_doc(MATERIAL_REQUEST, name)
	doc.check_permission("read")
	out = _serialize_mr(doc)
	out["actions"] = _mr_actions(doc)
	return out


@frappe.whitelist()
def save_material_request(name=None, project=None, schedule_date=None, items=None):
	"""Create / update a draft Material Request (Purchase type). One project for the
	whole request, stamped on every line + used to anchor the company."""
	items = frappe.parse_json(items) or []
	if not project:
		frappe.throw(_("Pick a project for the request."))

	if name and frappe.db.exists(MATERIAL_REQUEST, name):
		doc = frappe.get_doc(MATERIAL_REQUEST, name)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc(MATERIAL_REQUEST)
		doc.material_request_type = "Purchase"

	doc.company = _company_for(project)
	doc.project = project  # mandatory parent custom field on Material Request in this app
	doc.transaction_date = doc.transaction_date or nowdate()
	doc.schedule_date = schedule_date or doc.schedule_date

	# ERPNext requires a target warehouse on stock lines; the prototype has no
	# warehouse UI, so default to the company/project warehouse (harmless on services).
	default_wh = _default_warehouse(doc.company)
	doc.set("items", [])
	for row in items:
		if not row.get("item_code") or flt(row.get("qty")) <= 0:
			continue
		doc.append(
			"items",
			{
				"item_code": row.get("item_code"),
				"qty": flt(row.get("qty")),
				"uom": row.get("uom") or None,
				"rate": flt(row.get("rate")),
				"description": row.get("description") or None,
				"schedule_date": row.get("schedule_date") or schedule_date or nowdate(),
				"warehouse": default_wh,
				"project": project,
			},
		)
	if not doc.get("items"):
		frappe.throw(_("Add at least one item with a quantity."))

	doc.save()
	return _serialize_mr(doc)


@frappe.whitelist()
def submit_material_request(name):
	doc = frappe.get_doc(MATERIAL_REQUEST, name)
	doc.check_permission("submit")
	doc.submit()
	return get_material_request(name)


@frappe.whitelist()
def cancel_material_request(name):
	doc = frappe.get_doc(MATERIAL_REQUEST, name)
	doc.check_permission("cancel")
	doc.cancel()
	return get_material_request(name)


@frappe.whitelist()
def amend_material_request(name):
	src = frappe.get_doc(MATERIAL_REQUEST, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled request can be amended."))
	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	amended.insert()
	return get_material_request(amended.name)


@frappe.whitelist()
def delete_material_request(name):
	frappe.delete_doc(MATERIAL_REQUEST, name)
	return {"ok": True}


# ==========================================================================
# Purchase Order
# ==========================================================================


def _serialize_po(doc):
	return {
		"name": doc.name,
		"supplier": doc.supplier,
		"supplier_name": doc.supplier_name,
		"project": doc.project,
		"project_name": _project_name(doc.project),
		"transaction_date": str(doc.transaction_date) if doc.transaction_date else None,
		"schedule_date": str(doc.schedule_date) if doc.schedule_date else None,
		"currency": doc.currency,
		"grand_total": flt(doc.grand_total),
		"total": flt(doc.total),
		"per_received": flt(doc.per_received),
		"per_billed": flt(doc.per_billed),
		"docstatus": doc.docstatus,
		"state": _state(doc),
		"status": doc.status,
		"amended_from": doc.get("amended_from"),
		"terms": doc.terms,
		"tc_name": doc.tc_name,
		"company": doc.company,
		"items": [
			{
				"name": it.name,
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": it.description,
				"qty": flt(it.qty),
				"uom": it.uom,
				"rate": flt(it.rate),
				"amount": flt(it.amount),
				"received_qty": flt(it.received_qty),
				"warehouse": it.warehouse,
				"project": it.project,
			}
			for it in doc.items
		],
	}


def _po_actions(doc):
	if doc.docstatus == 0:
		return ["edit", "submit", "delete"]
	if doc.docstatus == 1:
		actions = ["cancel"]
		if flt(doc.per_received) < 100:
			actions.insert(0, "create_receipt")
		return actions
	return ["amend", "delete"]


@frappe.whitelist()
def get_purchase_order(name):
	doc = frappe.get_doc(PURCHASE_ORDER, name)
	doc.check_permission("read")
	out = _serialize_po(doc)
	out["actions"] = _po_actions(doc)
	return out


def _supplier_detail(supplier):
	"""Party block for the PO print view — tax id on the Supplier, contact
	person/phone/email on its native Contact (mirrors _subcontractor_detail)."""
	if not supplier or not frappe.db.exists("Supplier", supplier):
		return None
	detail = {"tax_id": frappe.db.get_value("Supplier", supplier, "tax_id")}
	contact = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", supplier],
		],
		fields=["first_name", "email_id", "mobile_no", "phone"],
		limit=1,
	)
	if contact:
		c = contact[0]
		detail["contact_person"] = c.first_name
		detail["email"] = c.email_id
		detail["phone"] = c.mobile_no or c.phone
	return detail


@frappe.whitelist()
def get_po_print_data(name):
	"""A Purchase Order enriched with the party/project detail the in-app print view
	needs (supplier contact + tax id, project code/location). Single fetch so the Vue
	print page mirrors the seeded Frappe Print Format from one payload."""
	doc = frappe.get_doc(PURCHASE_ORDER, name)
	doc.check_permission("read")
	out = _serialize_po(doc)
	out["supplier_detail"] = _supplier_detail(doc.supplier)
	out["project_detail"] = (
		frappe.db.get_value(
			"Project",
			doc.project,
			["custom_project_id", "customer", "location"],
			as_dict=True,
		)
		if doc.project
		else None
	)
	return out


@frappe.whitelist()
def get_mr_for_po(material_request):
	"""Prefill payload for a PO raised from an approved Material Request — the
	request's project and its still-to-order lines (qty net of already-ordered)."""
	doc = frappe.get_doc(MATERIAL_REQUEST, material_request)
	doc.check_permission("read")
	project = _mr_project(doc)
	lines = []
	for it in doc.items:
		remaining = flt(it.qty) - flt(it.ordered_qty)
		if remaining <= 0:
			continue
		lines.append(
			{
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": it.description,
				"qty": remaining,
				"uom": it.uom,
				"rate": flt(it.rate),
			}
		)
	return {
		"material_request": doc.name,
		"project": project,
		"project_name": _project_name(project),
		"lines": lines,
	}


@frappe.whitelist()
def save_purchase_order(
	name=None,
	supplier=None,
	project=None,
	transaction_date=None,
	schedule_date=None,
	items=None,
	terms=None,
	material_request=None,
):
	"""Create / update a draft Purchase Order. Rate is entered by hand (single
	company currency, conversion 1); line amounts are computed by the controller."""
	items = frappe.parse_json(items) or []
	if not supplier:
		frappe.throw(_("Pick a supplier."))
	if not project:
		frappe.throw(_("Pick a project."))

	if name and frappe.db.exists(PURCHASE_ORDER, name):
		doc = frappe.get_doc(PURCHASE_ORDER, name)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc(PURCHASE_ORDER)

	company = _company_for(project)
	doc.supplier = supplier
	doc.company = company
	doc.currency = _company_currency(company)
	doc.conversion_rate = 1
	doc.project = project
	doc.transaction_date = transaction_date or doc.transaction_date or nowdate()
	doc.schedule_date = schedule_date or doc.schedule_date
	doc.terms = terms

	# Stock lines need a delivery warehouse (see save_material_request); default it.
	default_wh = _default_warehouse(company)
	doc.set("items", [])
	for row in items:
		if not row.get("item_code") or flt(row.get("qty")) <= 0:
			continue
		doc.append(
			"items",
			{
				"item_code": row.get("item_code"),
				"qty": flt(row.get("qty")),
				"uom": row.get("uom") or None,
				"rate": flt(row.get("rate")),
				"description": row.get("description") or None,
				"schedule_date": row.get("schedule_date") or schedule_date or nowdate(),
				"warehouse": default_wh,
				"project": project,
				"material_request": material_request or None,
			},
		)
	if not doc.get("items"):
		frappe.throw(_("Add at least one item with a quantity."))

	doc.save()
	return _serialize_po(doc)


@frappe.whitelist()
def submit_purchase_order(name):
	doc = frappe.get_doc(PURCHASE_ORDER, name)
	doc.check_permission("submit")
	doc.submit()
	return get_purchase_order(name)


@frappe.whitelist()
def cancel_purchase_order(name):
	doc = frappe.get_doc(PURCHASE_ORDER, name)
	doc.check_permission("cancel")
	doc.cancel()
	return get_purchase_order(name)


@frappe.whitelist()
def amend_purchase_order(name):
	src = frappe.get_doc(PURCHASE_ORDER, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled order can be amended."))
	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	amended.insert()
	return get_purchase_order(amended.name)


@frappe.whitelist()
def delete_purchase_order(name):
	frappe.delete_doc(PURCHASE_ORDER, name)
	return {"ok": True}


# ==========================================================================
# Purchase Receipt — derived from a submitted Purchase Order
# ==========================================================================


def _make_purchase_receipt(source_po):
	"""ERPNext's PO → Purchase Receipt mapper. Its module moved in newer ERPNext
	(deployed prod may still carry the old location), so import defensively."""
	try:
		from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt
	except ImportError:
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
	return make_purchase_receipt(source_po)


def _default_warehouse(company=None):
	"""A receiving warehouse for the goods — ERPNext requires one on every stock line.
	Prefer Stock Settings' default, else the company's first non-group warehouse."""
	wh = frappe.db.get_single_value("Stock Settings", "default_warehouse")
	if wh and (not company or frappe.db.get_value("Warehouse", wh, "company") == company):
		return wh
	filters = {"is_group": 0, "disabled": 0}
	if company:
		filters["company"] = company
	return frappe.db.get_value("Warehouse", filters, "name")


def _serialize_pr(doc, ordered_by_poi=None):
	ordered_by_poi = ordered_by_poi or {}
	return {
		"name": doc.get("name"),
		"supplier": doc.supplier,
		"supplier_name": doc.supplier_name,
		"project": doc.project,
		"project_name": _project_name(doc.project),
		"posting_date": str(doc.posting_date) if doc.posting_date else None,
		"currency": doc.currency,
		"grand_total": flt(doc.grand_total),
		"per_billed": flt(doc.per_billed),
		"docstatus": doc.docstatus or 0,
		"state": _state(doc),
		"status": doc.get("status") or "Draft",
		"amended_from": doc.get("amended_from"),
		"purchase_order": next((it.purchase_order for it in doc.items if it.purchase_order), None),
		"warehouse": doc.get("set_warehouse")
		or next((it.warehouse for it in doc.items if it.warehouse), None),
		"company": doc.company,
		"items": [
			{
				"name": it.get("name"),
				"item_code": it.item_code,
				"item_name": it.item_name,
				"uom": it.uom,
				"rate": flt(it.rate),
				"received_qty": flt(it.received_qty),
				"ordered_qty": flt(ordered_by_poi.get(it.purchase_order_item, 0)),
				"amount": flt(it.amount),
				"warehouse": it.warehouse,
				"purchase_order": it.purchase_order,
				"purchase_order_item": it.purchase_order_item,
			}
			for it in doc.items
		],
	}


def _ordered_map(items):
	"""PO-item name → its ordered qty, for the 'ordered' column on the receipt form."""
	poi_names = [it.purchase_order_item for it in items if it.purchase_order_item]
	if not poi_names:
		return {}
	rows = frappe.get_all("Purchase Order Item", filters={"name": ["in", poi_names]}, fields=["name", "qty"])
	return {r.name: flt(r.qty) for r in rows}


@frappe.whitelist()
def get_open_purchase_orders():
	"""Submitted POs still awaiting delivery — the pick-list for a new receipt."""
	rows = frappe.get_list(
		PURCHASE_ORDER,
		filters=[
			["docstatus", "=", 1],
			["per_received", "<", 100],
			["status", "not in", ["Closed", "On Hold"]],
		],
		fields=["name", "supplier", "supplier_name", "project", "schedule_date", "grand_total"],
		order_by="transaction_date desc",
	)
	for r in rows:
		r["project_name"] = _project_name(r.project)
	return rows


@frappe.whitelist()
def get_receipt_draft(purchase_order):
	"""Build (unsaved) a receipt from a PO so the form shows the remaining-to-receive
	lines, pre-filled with warehouse + PO rate. Nothing is persisted until save."""
	try:
		target = _make_purchase_receipt(purchase_order)
	except Exception as e:  # fully received / closed / permission
		frappe.throw(_("Can't receive against {0}: {1}").format(purchase_order, str(e)))
	fallback = _default_warehouse(target.company)
	for it in target.items:
		it.warehouse = it.warehouse or fallback
		# Default the editable received qty to the still-outstanding quantity.
		it.received_qty = flt(it.received_qty) or flt(it.qty)
	return _serialize_pr(target, _ordered_map(target.items))


def _apply_receipt_lines(doc, lines, warehouse=None):
	"""Set each line's received qty from the payload; stamp a warehouse (chosen, else
	the line's own, else the company default) since stock lines require one; drop lines
	left at zero."""
	by_poi = {l.get("purchase_order_item"): l for l in lines if l.get("purchase_order_item")}
	by_item = {}
	for l in lines:
		by_item.setdefault(l.get("item_code"), l)
	fallback = warehouse or _default_warehouse(doc.company)
	for it in doc.items:
		match = by_poi.get(it.purchase_order_item) or by_item.get(it.item_code)
		qty = flt(match.get("received_qty")) if match else 0
		it.received_qty = qty
		it.qty = qty
		it.rejected_qty = 0
		it.warehouse = warehouse or it.warehouse or fallback
	doc.set("items", [it for it in doc.items if flt(it.received_qty) > 0])


@frappe.whitelist()
def save_purchase_receipt(name=None, purchase_order=None, posting_date=None, warehouse=None, items=None):
	"""Create / update a draft Purchase Receipt against a PO. New receipts are seeded
	from the PO mapper (warehouse, rate, links); the entered received quantities and
	the chosen receiving warehouse are applied and zero lines dropped."""
	lines = frappe.parse_json(items) or []

	if name and frappe.db.exists(PURCHASE_RECEIPT, name):
		doc = frappe.get_doc(PURCHASE_RECEIPT, name)
		doc.check_permission("write")
	elif purchase_order:
		doc = _make_purchase_receipt(purchase_order)
	else:
		frappe.throw(_("Pick a purchase order to receive against."))

	if warehouse:
		doc.set_warehouse = warehouse
	_apply_receipt_lines(doc, lines, warehouse)
	if not doc.get("items"):
		frappe.throw(_("Enter at least one received quantity."))
	doc.posting_date = posting_date or doc.get("posting_date") or nowdate()
	doc.set_posting_time = 1

	doc.save()
	return _serialize_pr(doc, _ordered_map(doc.items))


@frappe.whitelist()
def get_purchase_receipt(name):
	doc = frappe.get_doc(PURCHASE_RECEIPT, name)
	doc.check_permission("read")
	out = _serialize_pr(doc, _ordered_map(doc.items))
	if doc.docstatus == 0:
		out["actions"] = ["edit", "submit", "delete"]
	elif doc.docstatus == 1:
		out["actions"] = ["cancel"]
	else:
		out["actions"] = ["amend", "delete"]
	return out


@frappe.whitelist()
def submit_purchase_receipt(name):
	doc = frappe.get_doc(PURCHASE_RECEIPT, name)
	doc.check_permission("submit")
	doc.submit()
	return get_purchase_receipt(name)


@frappe.whitelist()
def cancel_purchase_receipt(name):
	doc = frappe.get_doc(PURCHASE_RECEIPT, name)
	doc.check_permission("cancel")
	doc.cancel()
	return get_purchase_receipt(name)


@frappe.whitelist()
def amend_purchase_receipt(name):
	src = frappe.get_doc(PURCHASE_RECEIPT, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled receipt can be amended."))
	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	amended.insert()
	return get_purchase_receipt(amended.name)


@frappe.whitelist()
def delete_purchase_receipt(name):
	frappe.delete_doc(PURCHASE_RECEIPT, name)
	return {"ok": True}
