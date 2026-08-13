# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Read-only MCP tools that return a plain, filtered record list — via
frappe.get_list, which — unlike frappe.get_all — applies
permission_query_conditions/has_permission so results stay scoped to whatever
the calling user can already see in the Desk / Vue app."""

import frappe
from frappe_mcp import ToolAnnotations

from buildsuite_core.mcp import mcp

_READ_ONLY = ToolAnnotations(readOnlyHint=True)


def _list_transactions(
	doctype,
	item_doctype,
	date_field,
	fields,
	project=None,
	item_code=None,
	status=None,
	from_date=None,
	to_date=None,
	limit=100,
	extra_filters=None,
):
	filters = [["docstatus", "=", 1], *(extra_filters or [])]
	if project:
		filters.append(["project", "=", project])
	if status:
		filters.append(["status", "=", status])
	if from_date:
		filters.append([date_field, ">=", from_date])
	if to_date:
		filters.append([date_field, "<=", to_date])
	if item_code:
		filters.append([item_doctype, "item_code", "=", item_code])
	return frappe.get_list(doctype, fields=fields, filters=filters, order_by=f"{date_field} desc", limit=limit)


@mcp.tool(annotations=_READ_ONLY)
def list_projects(limit: int = 100):
	"""List projects visible to the calling user, most recently modified first.

	Args:
		limit: Maximum number of projects to return (default 100).
	"""
	return frappe.get_list(
		"Project",
		fields=[
			"name",
			"project_name",
			"custom_project_id",
			"project_status",
			"percent_complete",
			"company",
			"project_manager",
			"expected_start_date",
			"expected_end_date",
		],
		order_by="modified desc",
		limit=limit,
	)


@mcp.tool(annotations=_READ_ONLY)
def list_material_requests(
	project: str | None = None,
	item_code: str | None = None,
	status: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 100,
):
	"""List submitted Material Requests, most recent first.

	Args:
		project: Filter to a single Project record name.
		item_code: Filter to requests containing this Item code.
		status: One of "Draft", "Submitted", "Stopped", "Cancelled", "Pending",
			"Partially Ordered", "Ordered", "Issued", "Transferred", "Received".
		from_date: Only requests on/after this date (YYYY-MM-DD), by transaction_date.
		to_date: Only requests on/before this date (YYYY-MM-DD), by transaction_date.
		limit: Maximum number of rows to return (default 100).
	"""
	return _list_transactions(
		"Material Request",
		"Material Request Item",
		"transaction_date",
		["name", "material_request_type", "transaction_date", "schedule_date", "status", "project", "company"],
		project=project,
		item_code=item_code,
		status=status,
		from_date=from_date,
		to_date=to_date,
		limit=limit,
	)


@mcp.tool(annotations=_READ_ONLY)
def list_purchase_orders(
	project: str | None = None,
	supplier: str | None = None,
	item_code: str | None = None,
	status: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 100,
):
	"""List submitted Purchase Orders, most recent first.

	Args:
		project: Filter to a single Project record name.
		supplier: Filter to a single Supplier record name.
		item_code: Filter to orders containing this Item code.
		status: One of "Draft", "On Hold", "To Receive and Bill", "To Bill",
			"To Receive", "Completed", "Cancelled", "Closed", "Delivered".
		from_date: Only orders on/after this date (YYYY-MM-DD), by transaction_date.
		to_date: Only orders on/before this date (YYYY-MM-DD), by transaction_date.
		limit: Maximum number of rows to return (default 100).
	"""
	return _list_transactions(
		"Purchase Order",
		"Purchase Order Item",
		"transaction_date",
		["name", "supplier", "transaction_date", "status", "project", "company", "grand_total"],
		project=project,
		item_code=item_code,
		status=status,
		from_date=from_date,
		to_date=to_date,
		limit=limit,
		extra_filters=[["supplier", "=", supplier]] if supplier else None,
	)


@mcp.tool(annotations=_READ_ONLY)
def list_purchase_receipts(
	project: str | None = None,
	item_code: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 100,
):
	"""List submitted Purchase Receipts, most recent first.

	Args:
		project: Filter to a single Project record name.
		item_code: Filter to receipts containing this Item code.
		from_date: Only receipts on/after this date (YYYY-MM-DD), by posting_date.
		to_date: Only receipts on/before this date (YYYY-MM-DD), by posting_date.
		limit: Maximum number of rows to return (default 100).
	"""
	return _list_transactions(
		"Purchase Receipt",
		"Purchase Receipt Item",
		"posting_date",
		["name", "supplier", "posting_date", "status", "project", "company", "grand_total"],
		project=project,
		item_code=item_code,
		from_date=from_date,
		to_date=to_date,
		limit=limit,
	)


@mcp.tool(annotations=_READ_ONLY)
def list_stock_entries(
	project: str | None = None,
	item_code: str | None = None,
	stock_entry_type: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	limit: int = 100,
):
	"""List submitted Stock Entries, most recent first.

	Args:
		project: Filter to a single Project record name.
		item_code: Filter to entries containing this Item code.
		stock_entry_type: Filter to a single Stock Entry Type (e.g. "Material Issue",
			"Material Receipt", "Material Transfer").
		from_date: Only entries on/after this date (YYYY-MM-DD), by posting_date.
		to_date: Only entries on/before this date (YYYY-MM-DD), by posting_date.
		limit: Maximum number of rows to return (default 100).
	"""
	return _list_transactions(
		"Stock Entry",
		"Stock Entry Detail",
		"posting_date",
		["name", "stock_entry_type", "posting_date", "project", "company"],
		project=project,
		item_code=item_code,
		from_date=from_date,
		to_date=to_date,
		limit=limit,
		extra_filters=[["stock_entry_type", "=", stock_entry_type]] if stock_entry_type else None,
	)
