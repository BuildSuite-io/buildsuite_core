# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""BOQ actuals — the cost-code actuals log (BuildSuite Core · BOQ Actuals & Commitments).

Real spend reaches the BOQ through the cost code, never through a BOQ record id. Three rails
produce actual cost — Material Consumption (Stock Entry / Material Issue), Subcontractor Bill,
and Expense Entry — each carrying a cost code (a group like "D" or an item like "D.02", scoped
to the project). Which BOQ a code lands on is decided at read time by the Approved revision.

This module is the "actuals log" as a DERIVED GETTER (decision D4, kept as a getter until
volume demands a real DocType): every contribution is computed live from the submitted source
documents, never hand-edited. Because it reads only submitted docs, cancelling a source removes
its entries for free (R3), and actuals resolve identically in every revision (R8). The summary
here is the single calculation path behind the BOQ Actual column (R2), and the same entries feed
the per-code drill-down (R1).

Rails (all post on Submit, reverse on Cancel):
  Material Consumption   qty x valuation rate  (Stock Entry.total_outgoing_value)  -> "Material"
  Subcontractor Bill     this-period amount    (Subcontractor Bill Line)           -> "Subcontract"
  Expense Entry          expense amount        (Expense Entry Table)               -> "Overhead"

Cost is recognised at consumption, not at purchase — a Purchase Receipt increases stock but
does not touch BOQ actual. The Subcontractor Work Order (Committed) is a separate promise and
lives in its own column (see subcontract.committed_by_cost_code), not here.
"""

import frappe
from frappe.utils import flt


def _material_entries(project):
	"""Submitted Material Issues (Stock Entry) charged to a cost code. The code lives on the
	Stock Entry header (one code per issue); the amount is the issue's outgoing value."""
	out = []
	rows = frappe.get_all(
		"Stock Entry",
		filters={
			"project": project,
			"docstatus": 1,
			"purpose": "Material Issue",
			"custom_cost_code_type": ["in", ["Group", "Item"]],
		},
		fields=[
			"name",
			"posting_date",
			"total_outgoing_value",
			"custom_cost_code_type",
			"custom_cost_code_group",
			"custom_cost_code_item",
			"custom_cost_code_label",
		],
	)
	for r in rows:
		if not (r.custom_cost_code_group or r.custom_cost_code_item):
			continue
		out.append(
			{
				"cost_code_type": r.custom_cost_code_type,
				"group_code": r.custom_cost_code_group or "",
				"item_code": r.custom_cost_code_item or "",
				"cost_type": "Material",
				"amount": flt(r.total_outgoing_value),
				"source_doctype": "Stock Entry",
				"source_name": r.name,
				"source_line": None,
				"party": None,
				"date": str(r.posting_date) if r.posting_date else None,
				"label": r.custom_cost_code_label or "",
			}
		)
	return out


def _subcontract_entries(project):
	"""Submitted Subcontractor Bill lines — this-period certified amount, by cost code."""
	bills = {
		b.name: b
		for b in frappe.get_all(
			"Subcontractor Bill",
			filters={"project": project, "docstatus": 1},
			fields=["name", "date", "subcontractor_name", "ra_no"],
		)
	}
	if not bills:
		return []
	out = []
	for l in frappe.get_all(
		"Subcontractor Bill Line",
		filters={"parent": ["in", list(bills)]},
		fields=[
			"name",
			"parent",
			"cost_code_type",
			"cost_code_group",
			"cost_code_item",
			"cost_code_label",
			"this_period_amount",
		],
	):
		if not (l.cost_code_group or l.cost_code_item) or flt(l.this_period_amount) == 0:
			continue
		b = bills[l.parent]
		out.append(
			{
				"cost_code_type": l.cost_code_type,
				"group_code": l.cost_code_group or "",
				"item_code": l.cost_code_item or "",
				"cost_type": "Subcontract",
				"amount": flt(l.this_period_amount),
				"source_doctype": "Subcontractor Bill",
				"source_name": l.parent,
				"source_line": l.name,
				"party": b.subcontractor_name,
				"date": str(b.date) if b.date else None,
				"label": l.cost_code_label or (f"Bill {b.ra_no}" if b.ra_no else ""),
			}
		)
	return out


def _expense_entries(project):
	"""Submitted Expense Entry lines charged to a cost code — informal direct cost."""
	heads = {
		e.name: e
		for e in frappe.get_all(
			"Expense Entry",
			filters={"project": project, "docstatus": 1},
			fields=["name", "date"],
		)
	}
	if not heads:
		return []
	out = []
	for r in frappe.get_all(
		"Expense Entry Table",
		filters={"parent": ["in", list(heads)]},
		fields=[
			"name",
			"parent",
			"cost_code_type",
			"cost_code_group",
			"cost_code_item",
			"cost_code_label",
			"amount",
			"expense_account_name",
			"description",
		],
	):
		if not (r.cost_code_group or r.cost_code_item) or flt(r.amount) == 0:
			continue
		e = heads[r.parent]
		out.append(
			{
				"cost_code_type": r.cost_code_type,
				"group_code": r.cost_code_group or "",
				"item_code": r.cost_code_item or "",
				"cost_type": "Overhead",
				"amount": flt(r.amount),
				"source_doctype": "Expense Entry",
				"source_name": r.parent,
				"source_line": r.name,
				"party": r.expense_account_name or None,
				"date": str(e.date) if e.date else None,
				"label": r.cost_code_label or r.description or "",
			}
		)
	return out


def _actual_entries(project):
	"""The full actuals log for a project — one line per contributing source line, across all
	three rails. Derived live from submitted documents (never stored). This is the single source
	the summary and the drill-down both read, so they can never disagree (R2)."""
	if not project:
		return []
	return _material_entries(project) + _subcontract_entries(project) + _expense_entries(project)


# The cost types a group row reports, in display order. A type with no source shows "— pending",
# never 0 — a zero claims there was nothing; an em-dash is the truth about our data.
COST_TYPES = ("Material", "Labour", "Plant", "Subcontract", "Overhead")


@frappe.whitelist()
def get_actuals_log(project, cost_type=None, from_date=None, to_date=None, source_doctype=None):
	"""The actuals log, optionally filtered by cost type / date range / source doctype (R4).
	Also the data source for cost-vs-budget."""
	entries = _actual_entries(project)
	if cost_type:
		entries = [e for e in entries if e["cost_type"] == cost_type]
	if source_doctype:
		entries = [e for e in entries if e["source_doctype"] == source_doctype]
	if from_date:
		entries = [e for e in entries if (e["date"] or "") >= from_date]
	if to_date:
		entries = [e for e in entries if (e["date"] or "") <= to_date]
	entries.sort(key=lambda e: (e["group_code"], e["item_code"], e["date"] or ""))
	return entries


@frappe.whitelist()
def get_actuals_summary(project):
	"""Per-code actual for the BOQ, plus the coverage split. An item-coded line credits its item
	AND its parent group (roll up, never down); group totals reconcile identically whether the
	lines beneath were coded fine or coarse. Returns:

	  by_group[code] = {actual, by_cost_type{}, item_coded, group_coded, items[]}
	  by_item[code]  = {actual, by_cost_type{}}

	`item_coded` vs `group_coded` drives the reader's coverage line ("₹X of ₹Y tracked at item
	level"). The frontend reads Actual from here — one calculation path, not two (R2)."""
	entries = _actual_entries(project)
	by_group = {}
	by_item = {}
	for e in entries:
		amt = flt(e["amount"])
		is_item = e["cost_code_type"] == "Item" and e["item_code"]
		if e["group_code"]:
			g = by_group.setdefault(
				e["group_code"],
				{"actual": 0, "by_cost_type": {}, "item_coded": 0, "group_coded": 0, "items": set()},
			)
			g["actual"] += amt
			g["by_cost_type"][e["cost_type"]] = g["by_cost_type"].get(e["cost_type"], 0) + amt
			if is_item:
				g["item_coded"] += amt
				g["items"].add(e["item_code"])
			else:
				g["group_coded"] += amt
		if is_item:
			it = by_item.setdefault(e["item_code"], {"actual": 0, "by_cost_type": {}})
			it["actual"] += amt
			it["by_cost_type"][e["cost_type"]] = it["by_cost_type"].get(e["cost_type"], 0) + amt
	for g in by_group.values():
		g["items"] = sorted(g["items"])
	return {
		"by_group": by_group,
		"by_item": by_item,
		"total": sum(flt(e["amount"]) for e in entries),
	}


@frappe.whitelist()
def get_actuals_for_code(project, group_code=None, item_code=None):
	"""The contributing entries behind one code, for the drill-down (R1). An item code returns
	only its own lines; a group code rolls up every line carrying that group (both group-coded
	and item-coded), never splitting a group-coded total down to items by guesswork."""
	entries = _actual_entries(project)
	if item_code:
		sel = [e for e in entries if e["item_code"] == item_code]
	elif group_code:
		sel = [e for e in entries if e["group_code"] == group_code]
	else:
		sel = []
	sel.sort(key=lambda e: (e["cost_type"], e["date"] or "", e["source_name"]))
	return {"entries": sel, "total": sum(flt(e["amount"]) for e in sel)}
