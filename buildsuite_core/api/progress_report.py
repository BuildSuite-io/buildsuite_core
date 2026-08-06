# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Project Progress Report — Daily / Weekly / Monthly (S167).

One aggregate read backing the Vue report surface: every project-scoped slice (tasks,
task progress entries, stages, material requests / purchase orders / receipts, scope
changes, attachments) rolled up against a moving date window. The window is set by the
caller:  period = daily | weekly | monthly, ending on `date` (today if omitted):
  daily   = the single day
  weekly  = the 7-day window ending on `date`
  monthly = the 30-day rolling window ending on `date`

Scoped to the project + its sub-projects, so the rollups capture subproject activity too.
Derived numbers are computed server-side so the Vue view stays a thin renderer."""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from buildsuite_core.api.project_dashboard import _subprojects

_ACTIVE_TASK_DONE = "Completed"
_SPANS = {"daily": 1, "weekly": 7, "monthly": 30}


def _window(period, end):
	"""(start, end) inclusive for the period ending on `end`."""
	span = _SPANS.get(period, 7)
	return add_days(end, -(span - 1)), end


def _in(d, start, end):
	return bool(d) and start <= getdate(d) <= end


@frappe.whitelist()
def get_progress_report(project, period="weekly", date=None):
	if not project or not frappe.db.exists("Project", project):
		frappe.throw(frappe._("Project not found."))
	period = period if period in _SPANS else "weekly"
	end = getdate(date) if date else getdate(nowdate())
	start, end = _window(period, end)
	today = getdate(nowdate())

	scope_ids = [project, *_subprojects(project)]

	proj = frappe.db.get_value(
		"Project",
		project,
		[
			"name",
			"project_name",
			"custom_project_id",
			"customer",
			"project_manager",
			"project_status",
			"expected_start_date",
			"expected_end_date",
		],
		as_dict=True,
	)
	client = ""
	if proj.customer:
		client = frappe.db.get_value("Customer", proj.customer, "customer_name") or proj.customer
	pm_name = frappe.db.get_value("User", proj.project_manager, "full_name") if proj.project_manager else ""

	# --- tasks in scope ---
	tasks = frappe.get_all(
		"Task",
		filters={"project": ["in", scope_ids]},
		fields=["name", "subject", "task_status", "progress", "exp_end_date"],
	)
	task_ids = [t.name for t in tasks] or ["__none__"]

	# latest progress-entry date per task (for "completed in period" + last-update)
	entries = frappe.get_all(
		"Task Progress Entry",
		filters={"task": ["in", task_ids]},
		fields=["name", "task", "entry_date", "skilled", "unskilled", "blocker", "blocker_detail", "owner"],
		order_by="entry_date desc, creation desc",
	)
	latest_entry = {}
	for e in entries:
		latest_entry.setdefault(e.task, e.entry_date)

	entries_in = [e for e in entries if _in(e.entry_date, start, end)]
	entry_task_ids = {e.task for e in entries_in}

	# --- status snapshot (current, not period-scoped) ---
	stats = {
		"total": len(tasks),
		"completed": 0,
		"in_progress": 0,
		"yet_to_start": 0,
		"delayed": 0,
		"blocked": 0,
		"overdue": 0,
	}
	_map = {
		"Completed": "completed",
		"In Progress": "in_progress",
		"Yet To Start": "yet_to_start",
		"In Delay": "delayed",
		"Blocked": "blocked",
	}
	for t in tasks:
		key = _map.get(t.task_status)
		if key:
			stats[key] += 1
		if t.task_status != _ACTIVE_TASK_DONE and t.exp_end_date and getdate(t.exp_end_date) < today:
			stats["overdue"] += 1

	tasks_completed_in = [
		t for t in tasks if t.task_status == _ACTIVE_TASK_DONE and _in(latest_entry.get(t.name), start, end)
	]
	task_activity = [
		{
			"id": t.name,
			"name": t.subject or t.name,
			"status": t.task_status or "Yet To Start",
			"progress": flt(t.progress),
			"last_update": str(latest_entry.get(t.name)) if latest_entry.get(t.name) else None,
		}
		for t in tasks
		if t.name in entry_task_ids
	]

	# --- labour + blockers (from period entries) ---
	skilled = sum(int(e.skilled or 0) for e in entries_in)
	unskilled = sum(int(e.unskilled or 0) for e in entries_in)
	task_name = {t.name: (t.subject or t.name) for t in tasks}
	blocker_entries = [e for e in entries_in if e.blocker]
	owners = {e.owner for e in blocker_entries if e.owner}
	owner_names = (
		dict(
			frappe.get_all(
				"User", filters={"name": ["in", list(owners)]}, fields=["name", "full_name"], as_list=True
			)
		)
		if owners
		else {}
	)
	blockers = [
		{
			"id": e.name,
			"task": task_name.get(e.task, e.task),
			"note": e.blocker_detail or "No detail provided.",
			"entry_date": str(e.entry_date) if e.entry_date else None,
			"owner": owner_names.get(e.owner, e.owner),
		}
		for e in blocker_entries
	]

	# --- stages touching the window ---
	stage_rows = frappe.get_all(
		"Stage Planning",
		filters={"project": ["in", scope_ids]},
		fields=[
			"name",
			"stage_name",
			"workflow_state",
			"planned_start",
			"planned_end",
			"description",
			"modified",
		],
	)
	stages = [
		{
			"id": s.name,
			"name": s.stage_name or s.name,
			"workflow_state": s.workflow_state or "Draft",
			"planned_start": str(s.planned_start) if s.planned_start else None,
			"planned_end": str(s.planned_end) if s.planned_end else None,
			"description": s.description or "",
		}
		for s in stage_rows
		if (
			(
				s.planned_start
				and s.planned_end
				and not (getdate(s.planned_end) < start or getdate(s.planned_start) > end)
			)
			or _in(s.modified, start, end)
		)
	]

	# --- materials (MR / PO raised, receipts) ---
	proj_in = {"project": ["in", scope_ids]}
	mrs = frappe.get_all("Material Request", filters=proj_in, fields=["name", "transaction_date"])
	mr_in = [m for m in mrs if _in(m.transaction_date, start, end)]
	pos = frappe.get_all(
		"Purchase Order", filters=proj_in, fields=["name", "transaction_date", "grand_total"]
	)
	po_in = [p for p in pos if _in(p.transaction_date, start, end)]
	po_value = sum(flt(p.grand_total) for p in po_in)

	prs = frappe.get_all(
		"Purchase Receipt",
		filters={**proj_in, "docstatus": 1},
		fields=["name", "posting_date", "supplier", "supplier_name", "status"],
	)
	pr_in = [g for g in prs if _in(g.posting_date, start, end)]
	grns = []
	for g in pr_in:
		first = frappe.get_all(
			"Purchase Receipt Item",
			filters={"parent": g.name},
			fields=["item_name", "received_qty", "uom"],
			order_by="idx",
			limit=1,
		)
		item = first[0] if first else {}
		grns.append(
			{
				"date": str(g.posting_date) if g.posting_date else None,
				"item": item.get("item_name") or "—",
				"supplier": g.supplier_name or g.supplier or "",
				"qty": flt(item.get("received_qty")),
				"uom": item.get("uom") or "",
				"status": g.status or "",
			}
		)

	# --- scope changes raised in the window ---
	sco_rows = frappe.get_all(
		"Scope Change Order",
		filters=proj_in,
		fields=["name", "raised_date", "title", "status", "impact", "recoverable"],
		order_by="raised_date desc",
	)
	sco_in = [s for s in sco_rows if _in(s.raised_date, start, end)]
	scope_changes = [
		{
			"id": s.name,
			"raised_date": str(s.raised_date) if s.raised_date else None,
			"title": s.title or s.name,
			"status": s.status or "",
			"impact": flt(s.impact),
			"recoverable": bool(s.recoverable),
		}
		for s in sco_in
	]
	scos_approved = sum(1 for s in sco_in if s.status == "Approved")
	scos_pending = sum(1 for s in sco_in if s.status == "Pending Approval")

	# --- attachments added on the project(s) in the window ---
	att_rows = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Project", "attached_to_name": ["in", scope_ids], "is_folder": 0},
		fields=["creation"],
	)
	attachments_added = sum(1 for a in att_rows if _in(a.creation, start, end))

	# --- look-ahead: tasks due in the next same-length window ---
	la_start = add_days(end, 1)
	la_end = add_days(la_start, _SPANS[period] - 1)
	look_ahead_tasks = sorted(
		[
			{
				"due": str(getdate(t.exp_end_date)),
				"name": t.subject or t.name,
				"status": t.task_status or "Yet To Start",
				"progress": flt(t.progress),
			}
			for t in tasks
			if t.task_status != _ACTIVE_TASK_DONE and _in(t.exp_end_date, la_start, la_end)
		],
		key=lambda r: r["due"],
	)

	return {
		"project": {
			"id": proj.name,
			"name": proj.project_name or proj.name,
			"code": proj.custom_project_id or proj.name,
			"client": client,
			"pm": proj.project_manager or "",
			"pm_name": pm_name or proj.project_manager or "",
			"status": proj.project_status or "New",
			"start_date": str(proj.expected_start_date) if proj.expected_start_date else None,
			"end_date": str(proj.expected_end_date) if proj.expected_end_date else None,
		},
		"period": period,
		"date": str(end),
		"window": {"start": str(start), "end": str(end)},
		"look_ahead": {"start": str(la_start), "end": str(la_end)},
		"task_stats": stats,
		"kpis": {
			"tasks_completed": len(tasks_completed_in),
			"entries": len(entries_in),
			"labour": {"skilled": skilled, "unskilled": unskilled, "total": skilled + unskilled},
			"deliveries": len(pr_in),
			"mr_count": len(mr_in),
			"po_count": len(po_in),
			"po_value": po_value,
			"blockers": len(blocker_entries),
			"scope_changes": len(sco_in),
			"scos_approved": scos_approved,
			"scos_pending": scos_pending,
			"attachments": attachments_added,
		},
		"task_activity": task_activity,
		"stages": stages,
		"materials": {
			"mr_count": len(mr_in),
			"po_count": len(po_in),
			"po_value": po_value,
			"grn_count": len(pr_in),
			"grns": grns,
		},
		"scope_changes": scope_changes,
		"blockers": blockers,
		"look_ahead_tasks": look_ahead_tasks,
	}
