# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Read-only MCP tools that return an aggregated/derived view (rollups, computed
totals) rather than a plain record list. These sum over frappe.qb, which — unlike
frappe.get_list — bypasses permission_query_conditions/has_permission entirely, so
each tool checks project read access explicitly before running its query."""

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt
from frappe_mcp import ToolAnnotations

from buildsuite_core.mcp import mcp

_READ_ONLY = ToolAnnotations(readOnlyHint=True)


def _check_project_read(project):
	if not frappe.has_permission("Project", "read", doc=project):
		frappe.throw(_("Not permitted to read this project."), frappe.PermissionError)


@mcp.tool(annotations=_READ_ONLY)
def get_item_consumption(project: str, item_code: str, from_date: str | None = None, to_date: str | None = None):
	"""Total quantity of an item issued to a project — the sum of the qty column
	across submitted Stock Entries of type "Material Issue".

	Args:
		project: The Project record name to scope to.
		item_code: The Item code to sum quantity for.
		from_date: Only entries on/after this date (YYYY-MM-DD), by posting_date.
		to_date: Only entries on/before this date (YYYY-MM-DD), by posting_date.
	"""
	_check_project_read(project)

	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	query = (
		frappe.qb.from_(se)
		.join(sed)
		.on(sed.parent == se.name)
		.select(Sum(sed.qty))
		.where(se.docstatus == 1)
		.where(se.stock_entry_type == "Material Issue")
		.where(se.project == project)
		.where(sed.item_code == item_code)
	)
	if from_date:
		query = query.where(se.posting_date >= from_date)
	if to_date:
		query = query.where(se.posting_date <= to_date)

	result = query.run()
	return {"project": project, "item_code": item_code, "qty_issued": flt(result[0][0]) if result else 0.0}


@mcp.tool(annotations=_READ_ONLY)
def get_material_received(project: str, item_code: str, from_date: str | None = None, to_date: str | None = None):
	"""Total quantity of an item received against a project — the sum of the
	received_qty column across submitted Purchase Receipts.

	Args:
		project: The Project record name to scope to.
		item_code: The Item code to sum quantity for.
		from_date: Only receipts on/after this date (YYYY-MM-DD), by posting_date.
		to_date: Only receipts on/before this date (YYYY-MM-DD), by posting_date.
	"""
	_check_project_read(project)

	pr = frappe.qb.DocType("Purchase Receipt")
	pri = frappe.qb.DocType("Purchase Receipt Item")
	query = (
		frappe.qb.from_(pr)
		.join(pri)
		.on(pri.parent == pr.name)
		.select(Sum(pri.received_qty))
		.where(pr.docstatus == 1)
		.where(pr.project == project)
		.where(pri.item_code == item_code)
	)
	if from_date:
		query = query.where(pr.posting_date >= from_date)
	if to_date:
		query = query.where(pr.posting_date <= to_date)

	result = query.run()
	return {"project": project, "item_code": item_code, "qty_received": flt(result[0][0]) if result else 0.0}
