# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Insights — line-level dataset rows for the prompt-driven Insights surface.

The Insights engine (frontend/src/data/insightEngine.js) crunches flat rows in the browser.
Most datasets are header-level and fetched client-side via the list adapter, but the LINE-level
ones (purchase-receipt lines, material-issue lines, expense lines, attendance rows) live in child
tables — and child DocTypes carry no standalone read permission, so a direct client `get_list`
403s. This endpoint reads each parent (honouring the caller's read permission on the PARENT
DocType) and joins its child rows server-side, returning the same flat shape the engine expects.

Only a persona that may read the parent gets rows; otherwise an empty list, mirroring the Vue
`canRead` gate. `frappe.get_all` is used for the child join (it bypasses the child's own perms),
which is safe because the parent-permission gate above already authorises the read.
"""

import frappe
from frappe.utils import flt


def _headers(doctype, filters, fields):
	"""Accessible parent rows keyed by name (empty if the caller can't read the DocType)."""
	if not frappe.has_permission(doctype, "read"):
		return {}
	return {r["name"]: r for r in frappe.get_all(doctype, filters=filters, fields=fields)}


@frappe.whitelist()
def line_dataset(dataset: str):
	"""Flattened rows for one line-level Insights dataset. See module docstring."""
	if dataset == "receiptLines":
		hdr = _headers(
			"Purchase Receipt",
			{"docstatus": 1},
			["name", "project", "supplier", "supplier_name", "posting_date"],
		)
		if not hdr:
			return []
		lines = frappe.get_all(
			"Purchase Receipt Item",
			filters={"parent": ["in", list(hdr)]},
			fields=["name", "parent", "item_code", "item_name", "uom", "received_qty", "amount"],
		)
		out = []
		for it in lines:
			h = hdr.get(it.parent)
			if not h:
				continue
			out.append(
				{
					"_key": it.name,
					"item": it.item_code,
					"item_name": it.item_name,
					"uom": it.uom,
					"receivedQty": flt(it.received_qty),
					"amount": flt(it.amount),
					"date": str(h.get("posting_date") or ""),
					"project": h.get("project"),
					"supplier": h.get("supplier_name") or h.get("supplier") or "—",
				}
			)
		return out

	if dataset == "consumptionLines":
		hdr = _headers(
			"Stock Entry",
			{"docstatus": 1, "stock_entry_type": "Material Issue"},
			["name", "project", "posting_date"],
		)
		if not hdr:
			return []
		lines = frappe.get_all(
			"Stock Entry Detail",
			filters={"parent": ["in", list(hdr)]},
			fields=["name", "parent", "item_code", "item_name", "qty", "uom"],
		)
		out = []
		for it in lines:
			h = hdr.get(it.parent)
			if not h:
				continue
			out.append(
				{
					"_key": it.name,
					"item": it.item_code,
					"item_name": it.item_name,
					"qty": flt(it.qty),
					"uom": it.uom,
					"date": str(h.get("posting_date") or ""),
					"project": h.get("project"),
				}
			)
		return out

	if dataset == "expenses":
		hdr = _headers("Expense Entry", {}, ["name", "date", "employee", "employee_name"])
		if not hdr:
			return []
		lines = frappe.get_all(
			"Expense Entry Table",
			filters={"parent": ["in", list(hdr)]},
			fields=[
				"name",
				"parent",
				"expense_account",
				"expense_account_name",
				"cost_code_label",
				"project",
				"employee",
				"employee_name",
				"amount",
			],
		)
		out = []
		for it in lines:
			h = hdr.get(it.parent) or {}
			out.append(
				{
					"_key": it.name,
					"amount": flt(it.amount),
					"costType": it.expense_account_name or it.cost_code_label or it.expense_account or "—",
					"project": it.project or h.get("project"),
					"employee": it.employee_name or it.employee or h.get("employee_name") or "—",
					"date": str(h.get("date") or ""),
				}
			)
		return out

	if dataset == "attendance":
		hdr = _headers("Field Attendance", {"docstatus": ["<", 2]}, ["name", "project", "date"])
		if not hdr:
			return []
		lines = frappe.get_all(
			"Field Attendance Employee",
			filters={"parent": ["in", list(hdr)]},
			fields=["name", "parent", "employee", "employee_name", "status"],
		)
		out = []
		for r in lines:
			h = hdr.get(r.parent)
			if not h:
				continue
			out.append(
				{
					"_key": r.name,
					"status": r.status,
					"employee": r.employee_name or r.employee or "—",
					"date": str(h.get("date") or ""),
					"project": h.get("project"),
				}
			)
		return out

	return []
