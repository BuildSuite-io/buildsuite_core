# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Material Consumption — a Stock Entry of type "Material Issue".

Draft only. Submitting is what moves the stock, and that is driven by a Frappe
Workflow when a site configures one — see api/workflow.py.

The store is derived from the project, never sent by the client: Warehouse
carries a `project` link and `create_warehouse_for_project` builds one per
project. Same rule the Desk client scripts follow.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

from buildsuite_core.utils.project import default_company
from buildsuite_core.utils.stock_entry import get_warehouse_from_project

STOCK_ENTRY = "Stock Entry"
MATERIAL_ISSUE = "Material Issue"

_ITEM_FIELDS = ("item_code", "qty", "uom")


@frappe.whitelist()
def get_site_stock(project: str) -> dict:
	"""Items on hand at a project's store.

	`actual_qty`, not `projected_qty` — material on order cannot be issued.
	"""
	warehouse = get_warehouse_from_project(project) if project else None
	if not warehouse:
		# Projects predating the warehouse hook have none — the form explains it.
		return {"warehouse": None, "rows": []}

	# get_list for Warehouse user permissions; its page length defaults to 20.
	rows = frappe.get_list(
		"Bin",
		filters={"warehouse": warehouse, "actual_qty": [">", 0]},
		fields=["item_code", "item_code.item_name", "actual_qty as available", "stock_uom as uom"],
		order_by="item_code asc",
		limit_page_length=0,
	)
	return {"warehouse": warehouse, "rows": rows}


@frappe.whitelist()
def get_material_consumption(name: str) -> dict:
	"""One entry with its items — a list read would not return child rows."""
	doc = frappe.get_doc(STOCK_ENTRY, name)
	doc.check_permission("read")  # get_doc does not check; only get_list does
	return _serialize(doc)


@frappe.whitelist()
def list_material_consumption(start=0, page_length=10, search=None, project=None) -> dict:
	"""One page of Material Issue entries + total_count for the pager."""
	filters = {"stock_entry_type": MATERIAL_ISSUE}
	if project:
		filters["project"] = project
	or_filters = [["name", "like", f"%{search}%"], ["remarks", "like", f"%{search}%"]] if search else None

	rows = frappe.get_list(
		STOCK_ENTRY,
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"posting_date",
			"project",
			"owner",
			"docstatus",
			"custom_cost_code_label as cost_code_label",
		],
		order_by="posting_date desc, name desc",
		start=cint(start),
		page_length=cint(page_length),
	)
	total_count = frappe.get_list(
		STOCK_ENTRY,
		filters=filters,
		or_filters=or_filters,
		fields=[{"COUNT": "name", "as": "count"}],
	)[0].count

	_attach_items(rows)
	return {"rows": rows, "total_count": total_count}


@frappe.whitelist(methods=["POST"])
def save_material_consumption(project=None, items=None, cost_code=None, name=None) -> dict:
	"""Create or update a draft Material Issue.

	No posting date is accepted — Stock Entry defaults it to today.
	"""
	rows = _parse_items(items)
	if not project:
		frappe.throw(_("Project is required."))
	if not rows:
		frappe.throw(_("Add at least one item."))

	warehouse = get_warehouse_from_project(project)
	if not warehouse:
		frappe.throw(_("This project has no store, so nothing can be issued from it."))

	if name:
		if not frappe.db.exists(STOCK_ENTRY, name):
			# A stale id would otherwise create a second entry.
			frappe.throw(_("Consumption {0} no longer exists.").format(name))
		doc = frappe.get_doc(STOCK_ENTRY, name)
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft can be edited."))
	else:
		doc = frappe.new_doc(STOCK_ENTRY)
		doc.stock_entry_type = MATERIAL_ISSUE

	doc.project = project
	# The project's company, not the user's default — the store was created under
	# the project's company, and a mismatch fails validation on a multi-company site.
	doc.company = frappe.db.get_value("Project", project, "company") or default_company()
	doc.from_warehouse = warehouse
	_apply_cost_code(doc, cost_code)

	doc.set("items", [])
	for row in rows:
		doc.append("items", {**{k: row.get(k) for k in _ITEM_FIELDS}, "s_warehouse": warehouse})

	doc.save()  # checks write / create permission itself
	return _serialize(doc)


def _serialize(doc) -> dict:
	return {
		"name": doc.name,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name"),
		"posting_date": str(doc.posting_date) if doc.posting_date else None,
		"purpose": doc.purpose,
		"owner": doc.owner,
		"docstatus": doc.docstatus,
		"cost_code_type": doc.get("custom_cost_code_type"),
		"cost_code_group": doc.get("custom_cost_code_group"),
		"cost_code_item": doc.get("custom_cost_code_item"),
		"cost_code_label": doc.get("custom_cost_code_label"),
		"items": [
			{"item_code": r.item_code, "item_name": r.item_name, "qty": r.qty, "uom": r.uom}
			for r in doc.items
		],
	}


def _parse_items(payload) -> list:
	"""A JSON object parses to a truthy _dict and would iterate its keys."""
	rows = frappe.parse_json(payload) or []
	if not isinstance(rows, list):
		frappe.throw(_("Expected a list of items."))

	rows = [r for r in rows if r and r.get("item_code")]
	if any(flt(r.get("qty")) <= 0 for r in rows):
		frappe.throw(_("Every item needs a quantity above zero."))
	return rows


def _apply_cost_code(doc, payload) -> None:
	"""Flatten the picker's selection. The group is kept even for an item pick,
	so cost rolls up either way."""
	cc = frappe.parse_json(payload) if payload else None
	cc = cc if isinstance(cc, dict) else {}
	doc.custom_cost_code_type = ("Item" if cc.get("type") == "item" else "Group") if cc else ""
	doc.custom_cost_code_group = cc.get("group_code") or ""
	doc.custom_cost_code_item = cc.get("item_code") or ""
	doc.custom_cost_code_label = cc.get("label") or ""


def _attach_items(rows: list) -> None:
	"""Stamp each entry with its items — one query for the page.

	`parent_doctype` is required; this Frappe version rejects `parent=`.
	"""
	if not rows:
		return

	lines = frappe.get_all(
		"Stock Entry Detail",
		filters={"parent": ["in", [r.name for r in rows]]},
		fields=["parent", "item_name", "item_code", "qty", "uom"],
		order_by="idx asc",
		parent_doctype=STOCK_ENTRY,
	)
	by_parent: dict[str, list[dict]] = {}
	for line in lines:
		by_parent.setdefault(line.parent, []).append(
			{"label": line.item_name or line.item_code, "qty": line.qty, "uom": line.uom}
		)
	for row in rows:
		row.items = by_parent.get(row.name, [])
