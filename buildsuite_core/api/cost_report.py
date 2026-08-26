# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Cost vs Budget by Cost Code — the project cost-control report launched from the project
overview. Per BOQ cost code, grouped by cost type, it reconciles three figures computed live:

  • Planned   — Σ BOQ Item.planned_amount over the project's Approved BOQ(s), by group code.
  • Committed — submitted Subcontractor Work Order lines by cost-code group
                (subcontract.committed_by_cost_code) — scope already promised to subcontractors.
  • Actual    — recognised spend by cost code across every rail (material issues, subcontractor
                bills, overheads) via boq_actuals.get_actuals_summary. Cost is recognised at
                consumption, not purchase, so this never double-counts a PO.

Variance = Actual − Planned (over budget is positive), mirroring the report prototype; Committed
is shown alongside but is deliberately NOT folded into Variance. A code's cost type is its group's
dominant BOQ Item.cost_head (by planned amount), so rows group by the same vocabulary Planned is
expressed in — sidestepping the Planned/Actual cost-head vocabulary mismatch.

Only Approved BOQs count (a draft/superseded revision must never be costed against). The endpoint
returns flat rows; the view groups by cost type and filters (variance threshold, cost type, search)
client-side, exactly like the sibling bespoke reports.
"""

import frappe
from frappe.utils import flt

from buildsuite_core.api import boq_actuals, subcontract


@frappe.whitelist()
def cost_vs_budget_by_cost_code(project: str):
	"""Planned / Committed / Actual / Variance per BOQ cost code for a project.

	Returns ``{project, boq, rows: [{key, code, name, costType, planned, committed, actual,
	variance, variancePct}]}``. ``rows`` is empty (and ``boq`` is ``None``) when the project has
	no Approved BOQ — there is nothing to measure cost against yet.
	"""
	if not project:
		return {"project": project, "boq": None, "rows": []}

	# Only Approved BOQs are authoritative for costing (mirrors get_project_cost_codes).
	boqs = frappe.get_all("BOQ", filters={"project": project, "status": "Approved"}, pluck="name")

	# Committed + Actual are project-scoped and keyed by the group cost-code string, so Planned is
	# aggregated by that same string below — the three maps line up on the group code.
	committed = subcontract.committed_by_cost_code(project) or {}
	actual_by_group = (boq_actuals.get_actuals_summary(project) or {}).get("by_group", {})

	rows = []
	if boqs:
		groups = frappe.get_all(
			"BOQ Group",
			filters={"boq": ["in", boqs]},
			fields=["name", "code", "group_name"],
		)
		items = frappe.get_all(
			"BOQ Item",
			filters={"boq": ["in", boqs]},
			fields=["boq_group", "planned_amount", "cost_head"],
		)
		items_by_group = {}
		for it in items:
			items_by_group.setdefault(it.boq_group, []).append(it)

		# Aggregate Planned by group code. Codes are stable across BOQ revisions, so combining is
		# correct if two Approved revisions share one — and Committed/Actual already key on the code.
		agg = {}  # code -> {name, planned, heads{cost_head: planned}}
		for g in groups:
			code = g.code or ""
			if not code:
				continue
			bucket = agg.setdefault(code, {"name": g.group_name, "planned": 0.0, "heads": {}})
			for it in items_by_group.get(g.name, []):
				amt = flt(it.planned_amount)
				bucket["planned"] += amt
				if it.cost_head:
					bucket["heads"][it.cost_head] = bucket["heads"].get(it.cost_head, 0) + amt

		for code, b in agg.items():
			planned = b["planned"]
			cost_type = max(b["heads"], key=b["heads"].get) if b["heads"] else "Unclassified"
			committed_amt = flt(committed.get(code, 0))
			actual_amt = flt((actual_by_group.get(code) or {}).get("actual", 0))
			variance = actual_amt - planned
			rows.append(
				{
					"key": code,
					"code": code,
					"name": b["name"],
					"costType": cost_type,
					"planned": planned,
					"committed": committed_amt,
					"actual": actual_amt,
					"variance": variance,
					"variancePct": (variance / planned * 100) if planned else 0,
				}
			)

	rows.sort(key=lambda r: r["code"])
	return {"project": project, "boq": boqs[0] if boqs else None, "rows": rows}
