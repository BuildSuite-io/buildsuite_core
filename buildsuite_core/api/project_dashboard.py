# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Dashboard — the Site Execution owner/PM view (S251). One aggregate read backing the
Vue dashboard, scoped to the whole portfolio or a single project (+ its sub-projects):

  · KPIs        — active projects + at-risk, contract value (BOQ planned/budget), work done
                  (BOQ earned value), and schedule (avg progress vs expected).
  · health      — per project: progress vs expected, earned/contract, open tasks, risk reasons.
  · cost_heads  — actual spend by head where a live source exists (Subcontractor bills,
                  Machinery usage); Labour/Material/Overhead are pending (no cost-type source).
  · decision    — approvals waiting on the owner (stage plans, SCOs, material requests, petty).
  · commitments — subcontract committed/billed/remaining, POs on order, retention held.
  · activity    — last 7 days of site reporting (progress entries, blockers, deliveries).
  · attention   — project-level risks + overdue tasks.

Derived numbers are computed server-side so the payload stays small. Single-company for now."""

import math

import frappe
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

from buildsuite_core.utils.project import default_company

_ACTIVE = ("New", "Ongoing", "Delayed")
_BOQ_RANK = {"Approved": 2, "Submitted": 1}
_HEALTH_LIMIT = 10


# --------------------------------------------------------------------------- #
# Scope
# --------------------------------------------------------------------------- #
def _subprojects(project):
	out, stack = [], [project]
	while stack:
		cur = stack.pop()
		kids = frappe.get_all("Project", filters={"parent_project": cur}, pluck="name")
		out.extend(kids)
		stack.extend(kids)
	return out


# --------------------------------------------------------------------------- #
# Per-project schedule / cost / risk
# --------------------------------------------------------------------------- #
def _schedule(today, start, end, progress):
	"""(expected_pct, days_to_end, delayed_days, variance_pct). Positive variance = behind."""
	days_to_end = date_diff(end, today) if end else None
	if not start or not end:
		return 0.0, days_to_end, 0, 0.0
	span = date_diff(end, start)
	if span <= 0:
		return 0.0, days_to_end, 0, 0.0
	expected = max(0.0, min(100.0, date_diff(today, start) / span * 100.0))
	variance = ((expected - progress) / expected * 100.0) if expected > 0 else 0.0
	progress_slip = math.ceil((expected - progress) / 100.0 * span) if expected > progress else 0
	overdue = date_diff(today, end)
	overdue_days = overdue if (overdue > 0 and progress < 100) else 0
	return expected, days_to_end, max(progress_slip, overdue_days), variance


def _reasons(delayed, variance, days_to_end, progress):
	out = []
	if delayed > 0:
		out.append(f"{delayed}d behind schedule")
	elif variance > 10:
		out.append(f"{round(variance)}% behind pace")
	if days_to_end is not None and days_to_end < 0 and progress < 100:
		out.append("past deadline")
	return out


def _current_boq(project_names):
	if not project_names:
		return {}
	rows = frappe.get_all(
		"BOQ",
		filters={"project": ["in", project_names]},
		fields=["project", "status", "planned_amount", "actual_amount"],
		order_by="creation desc",
	)
	best = {}
	for b in rows:
		cur = best.get(b.project)
		if not cur or _BOQ_RANK.get(b.status, 0) > _BOQ_RANK.get(cur.status, 0):
			best[b.project] = b
	return {p: (flt(b.planned_amount), flt(b.actual_amount)) for p, b in best.items()}


def _sum(doctype, filters, field):
	from frappe.query_builder.functions import Sum

	dt = frappe.qb.DocType(doctype)
	q = frappe.qb.from_(dt).select(Sum(getattr(dt, field)))
	for k, v in filters.items():
		col = getattr(dt, k)
		q = q.where(col.isin(v[1])) if isinstance(v, (list, tuple)) and v[0] == "in" else q.where(col == v)
	return flt(q.run()[0][0])


@frappe.whitelist()
def get_project_dashboard(project=None):
	company = default_company()
	today = getdate(nowdate())
	since = add_days(today, -7)

	# --- scope: one project (+ subs) or the whole portfolio ---
	if project:
		roots = frappe.get_all(
			"Project",
			filters={"name": project},
			fields=[
				"name",
				"project_name",
				"customer",
				"status",
				"project_status",
				"percent_complete",
				"expected_start_date",
				"expected_end_date",
				"estimated_costing",
			],
		)
		scope_ids = [project, *_subprojects(project)]
	else:
		roots = frappe.get_all(
			"Project",
			filters={"company": company, "parent_project": ["in", ["", None]]},
			fields=[
				"name",
				"project_name",
				"customer",
				"status",
				"project_status",
				"percent_complete",
				"expected_start_date",
				"expected_end_date",
				"estimated_costing",
			],
			order_by="modified desc",
		)
		scope_ids = frappe.get_all("Project", filters={"company": company}, pluck="name")
	scope_ids = scope_ids or ["__none__"]
	proj_in = {"project": ["in", scope_ids]}

	boq = _current_boq([p.name for p in roots])
	customers = {p.customer for p in roots if p.customer}
	cust_names = (
		dict(
			frappe.get_all(
				"Customer",
				filters={"name": ["in", list(customers)]},
				fields=["name", "customer_name"],
				as_list=True,
			)
		)
		if customers
		else {}
	)

	# --- per-root rows ---
	rows = []
	for p in roots:
		planned, earned = boq.get(p.name, (flt(p.estimated_costing), None))
		has_boq = p.name in boq
		progress = flt(p.percent_complete)
		expected, days_to_end, delayed, variance = _schedule(
			today, p.expected_start_date, p.expected_end_date, progress
		)
		active = p.project_status in _ACTIVE and p.status != "Cancelled"
		reasons = _reasons(delayed, variance, days_to_end, progress) if active else []
		rows.append(
			{
				"id": p.name,
				"name": p.project_name or p.name,
				"client": cust_names.get(p.customer, p.customer) or "",
				"status": p.project_status or "New",
				"progress": round(progress, 1),
				"expected": round(expected, 1),
				"days_to_end": days_to_end,
				"delayed": delayed,
				"variance": round(variance, 1),
				"planned": flt(planned),
				"earned": flt(earned) if earned is not None else None,
				"has_boq": has_boq,
				"reasons": reasons,
				"active": active,
			}
		)

	active_rows = [r for r in rows if r["active"]]
	at_risk = [r for r in active_rows if r["reasons"]]

	# --- KPIs ---
	total_planned = sum(r["planned"] for r in active_rows)
	total_earned = sum((r["earned"] or 0) for r in active_rows)
	with_boq = sum(1 for r in active_rows if r["has_boq"])
	avg_progress = (sum(r["progress"] for r in active_rows) / len(active_rows)) if active_rows else 0
	avg_expected = (sum(r["expected"] for r in active_rows) / len(active_rows)) if active_rows else 0
	behind = sum(1 for r in active_rows if r["delayed"] > 0)
	worst_delay = max((r["delayed"] for r in active_rows), default=0)

	# --- health rows: the scoped project(s), else the most at-risk active ---
	health_src = rows if project else sorted(active_rows, key=lambda r: (-r["delayed"], -r["variance"]))
	health = health_src[:_HEALTH_LIMIT]
	# open / total tasks for just the shown rows
	for r in health:
		ids = [r["id"], *_subprojects(r["id"])] if not project else scope_ids
		total = frappe.db.count("Task", {"project": ["in", ids]})
		done = frappe.db.count("Task", {"project": ["in", ids], "status": "Completed"})
		r["open_tasks"] = total - done
		r["total_tasks"] = total

	# --- cost booked by head (live sources only) ---
	subcontractor = _sum("Subcontractor Bill", {**proj_in, "docstatus": 1}, "gross")
	mu = frappe.get_all(
		"Machinery Usage", filters={**proj_in, "docstatus": 1}, fields=["rate", "quantity", "fuel_cost"]
	)
	machinery = sum(flt(m.rate) * flt(m.quantity) + flt(m.fuel_cost) for m in mu)
	cost_total = subcontractor + machinery
	cost_heads = [
		{"key": "subcontractor", "label": "Subcontractor", "value": subcontractor, "bar": "bg-info-500"},
		{"key": "machinery", "label": "Machinery", "value": machinery, "bar": "bg-warning-500"},
		{"key": "labour", "label": "Labour", "value": 0, "bar": "bg-brand-500", "pending": True},
		{"key": "material", "label": "Material", "value": 0, "bar": "bg-ink-300", "pending": True},
		{"key": "overhead", "label": "Overhead", "value": 0, "bar": "bg-ink-400", "pending": True},
	]
	_mx = max([subcontractor, machinery, 1])
	for h in cost_heads:
		h["pct"] = 0 if h.get("pending") else h["value"] / _mx * 100

	# --- decision queue ---
	stage_ct = frappe.db.count("Stage Planning", {**proj_in, "workflow_state": "Pending Approval"})
	scos = frappe.get_all(
		"Scope Change Order",
		filters={**proj_in, "status": "Pending Approval"},
		fields=["name", "title", "project", "project_name", "impact", "raised_date"],
	)
	sco_value = sum(flt(s.impact) for s in scos)
	mr_ct = frappe.db.count("Material Request", {**proj_in, "docstatus": 0})
	petty = frappe.get_all(
		"Petty Cash Request", filters={**proj_in, "status": "Requested"}, fields=["amount"]
	)
	decision = [
		{
			"key": "stage",
			"label": "Stage plans",
			"count": stage_ct,
			"value": None,
			"sub": "awaiting your approval",
			"slug": "check-circle",
			"tone": "bg-brand-50 text-brand-700",
			"to": "/stage-plannings?status=Pending Approval",
		},
		{
			"key": "sco",
			"label": "Scope changes",
			"count": len(scos),
			"value": sco_value,
			"sub": "cost impact pending",
			"slug": "refresh-ccw",
			"tone": "bg-warning-50 text-warning-700",
			"to": "/sco",
		},
		{
			"key": "mr",
			"label": "Material requests",
			"count": mr_ct,
			"value": None,
			"sub": "to approve for ordering",
			"slug": "procurement",
			"tone": "bg-info-50 text-info-700",
			"to": "/procurement/material-requests",
		},
		{
			"key": "petty",
			"label": "Petty cash",
			"count": len(petty),
			"value": sum(flt(r.amount) for r in petty),
			"sub": "requested by site",
			"slug": "wallet",
			"tone": "bg-success-50 text-success-700",
			"to": "/project-finance/petty-cash",
		},
	]

	# --- commitments ---
	committed = _sum("Subcontractor Work Order", {**proj_in, "docstatus": 1}, "total_value")
	billed = _sum("Subcontractor Bill", {**proj_in, "docstatus": 1}, "gross")
	retention = _sum("Subcontractor Bill", {**proj_in, "docstatus": 1}, "retention_amount")
	pos = frappe.get_all(
		"Purchase Order",
		filters={
			**proj_in,
			"docstatus": 1,
			"status": ["not in", ["Closed", "Cancelled"]],
			"per_received": ["<", 100],
		},
		fields=["grand_total"],
	)
	commitments = {
		"committed": committed,
		"billed": billed,
		"remaining": max(0.0, committed - billed),
		"on_order": sum(flt(p.grand_total) for p in pos),
		"on_order_count": len(pos),
		"retention": retention,
	}

	# --- site activity (7d). Task Progress Entry has no `project` — scope it via task. ---
	if project:
		task_ids = frappe.get_all("Task", filters={"project": ["in", scope_ids]}, pluck="name") or [
			"__none__"
		]
		tpe_scope = {"task": ["in", task_ids]}
	else:
		tpe_scope = {}  # portfolio = company-wide
	tpe = frappe.get_all(
		"Task Progress Entry",
		filters={**tpe_scope, "entry_date": [">=", str(since)]},
		fields=["owner", "blocker"],
	)
	recent = frappe.get_all(
		"Task Progress Entry",
		filters=tpe_scope,
		fields=["name", "task", "entry_date", "cumulative_progress", "blocker", "owner"],
		order_by="entry_date desc, creation desc",
		limit=5,
	)
	task_names = list({r.task for r in recent if r.task})
	task_subjects = (
		dict(
			frappe.get_all(
				"Task", filters={"name": ["in", task_names]}, fields=["name", "subject"], as_list=True
			)
		)
		if task_names
		else {}
	)
	last = frappe.get_all(
		"Task Progress Entry",
		filters=tpe_scope,
		fields=["entry_date"],
		order_by="entry_date desc",
		limit=1,
	)
	activity = {
		"entries": len(tpe),
		"reporters": len({e.owner for e in tpe}),
		"blockers": sum(1 for e in tpe if e.blocker),
		"receipts": frappe.db.count(
			"Purchase Receipt",
			{"project": ["in", scope_ids], "docstatus": 1, "posting_date": [">=", str(since)]},
		),
		"man_days": None,  # no attendance source yet
		"last_activity_date": str(last[0].entry_date) if last else None,
		"recent": [
			{
				"id": r.name,
				"task": task_subjects.get(r.task, r.task),
				"entry_date": str(r.entry_date) if r.entry_date else None,
				"progress": flt(r.cumulative_progress),
				"blocker": bool(r.blocker),
				"owner": r.owner,
			}
			for r in recent
		],
	}

	# --- needs attention ---
	attention = [
		{
			"key": f"risk-{r['id']}",
			"tone": "bg-danger-500",
			"kind": "Project at risk",
			"title": " · ".join(r["reasons"]),
			"context": r["name"],
			"to": f"/projects/{r['id']}",
		}
		for r in at_risk[:6]
	]
	overdue = frappe.db.count(
		"Task",
		{"project": ["in", scope_ids], "status": ["!=", "Completed"], "exp_end_date": ["<", str(today)]},
	)
	if overdue:
		attention.append(
			{
				"key": "overdue-tasks",
				"tone": "bg-warning-500",
				"kind": "Overdue tasks",
				"title": f"{overdue} task{'s' if overdue != 1 else ''} past their end date and still open",
				"context": "Across projects in scope",
				"to": "/tasks?status=overdue",
			}
		)

	return {
		"scoped": bool(project),
		"kpis": {
			"active_projects": len(active_rows),
			"at_risk": len(at_risk),
			"contract_value": total_planned,
			"work_done": total_earned,
			"earned_pct": round((total_earned / total_planned * 100.0), 0) if total_planned else 0,
			"boq_with": with_boq,
			"boq_total": len(active_rows),
			"avg_progress": round(avg_progress, 0),
			"avg_expected": round(avg_expected, 0),
			"behind": behind,
			"worst_delay": worst_delay,
		},
		"health": health,
		"total_projects": len(rows),
		"cost": {"total_actual": cost_total, "heads": cost_heads},
		"decision": decision,
		"decision_total": sum(d["count"] for d in decision),
		"commitments": commitments,
		"activity": activity,
		"attention": attention,
	}
