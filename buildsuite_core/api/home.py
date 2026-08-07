# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Home dashboard — the app-wide snapshot backing AppHomeView (`/home`) and the denser
Desk overview DashboardView (`/dashboard`). One aggregate read so both views are thin
renderers (mirrors api/project_dashboard.py):

  · kpis     — active projects, open + overdue tasks, pending SCOs, progress filed today,
               users, and the total order book (BOQ contract value of active projects).
  · projects — active root projects with progress + a schedule tone (for the bar colour).
  · pending_scos      — Scope Change Orders awaiting approval (title + cost impact).
  · tasks_in_progress — the Working tasks, with their assignee.

Scoped to the logged-in user: every project/task/SCO count goes through get_list, so the
Project/Task permission query conditions apply — a team-scoped user (QS, Site Engineer, …)
sees only their own projects + tasks, matching the Projects list; admins/PMs see the whole
company. Derived numbers are computed server-side so the payload stays small. Single-company
for now."""

import json

import frappe
from frappe.utils import date_diff, flt, getdate, nowdate

from buildsuite_core.utils.project import default_company

_ACTIVE = ("New", "Ongoing", "Delayed")
_BOQ_RANK = {"Approved": 2, "Submitted": 1}
_PROJECT_LIMIT = 12
_TASK_LIMIT = 6
_SCO_LIMIT = 8
_OPEN_TASK = ("Completed", "Cancelled", "Template")


def _current_boq(project_names):
	"""The best current BOQ per project (Approved > Submitted > latest) → planned amount."""
	if not project_names:
		return {}
	rows = frappe.get_all(
		"BOQ",
		filters={"project": ["in", project_names]},
		fields=["project", "status", "planned_amount"],
		order_by="creation desc",
	)
	best = {}
	for b in rows:
		cur = best.get(b.project)
		if not cur or _BOQ_RANK.get(b.status, 0) > _BOQ_RANK.get(cur.status, 0):
			best[b.project] = b
	return {p: flt(b.planned_amount) for p, b in best.items()}


def _expected_pct(today, start, end):
	"""Schedule-expected % complete for `today` given the planned window (0 if undated)."""
	if not start or not end:
		return 0.0
	span = date_diff(end, start)
	if span <= 0:
		return 0.0
	return max(0.0, min(100.0, date_diff(today, start) / span * 100.0))


def _tone(expected, progress):
	"""Schedule-variance tone for the progress bar, same convention as the Projects list."""
	if expected <= 0:
		return "success"
	variance = (expected - progress) / expected * 100.0
	if variance > 15:
		return "danger"
	if variance > 5:
		return "warning"
	return "success"


def _first_assignee(assign):
	"""ERPNext stores assignments as a JSON list in `_assign`; take the first."""
	if not assign:
		return None
	try:
		users = json.loads(assign)
		return users[0] if users else None
	except (ValueError, TypeError):
		return None


@frappe.whitelist()
def get_home_dashboard():
	company = default_company()
	today = getdate(nowdate())

	# Use get_list (not get_all/db.count) so the Project/Task permission query conditions
	# apply: a scoped user (QS, Site Engineer, …) sees only their team's projects + tasks,
	# matching the Projects list. Admins/PMs are unscoped and still see the whole company.
	# get_list defaults to a 20-row page, so limit_page_length=0 is required to count all.
	project_ids = frappe.get_list(
		"Project", filters={"company": company}, pluck="name", limit_page_length=0
	) or ["__none__"]
	proj_in = {"project": ["in", project_ids]}

	# --- active root projects → the list + the order book (team-scoped) ---
	roots = frappe.get_list(
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
			"project_manager",
		],
		order_by="modified desc",
		limit_page_length=0,
	)
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

	projects, order_book, active_ct = [], 0.0, 0
	for p in roots:
		if not (p.project_status in _ACTIVE and p.status != "Cancelled"):
			continue
		active_ct += 1
		planned = boq.get(p.name, flt(p.estimated_costing))
		order_book += flt(planned)
		progress = flt(p.percent_complete)
		expected = _expected_pct(today, p.expected_start_date, p.expected_end_date)
		if len(projects) < _PROJECT_LIMIT:
			projects.append(
				{
					"id": p.name,
					"name": p.project_name or p.name,
					"client": cust_names.get(p.customer, p.customer) or "",
					"status": p.project_status or "New",
					"progress": round(progress, 1),
					"budget": flt(planned),
					"pm": p.project_manager or "",
					"tone": _tone(expected, progress),
				}
			)

	# --- task + SCO counts (company-scoped via project) ---
	open_tasks = frappe.db.count("Task", {**proj_in, "status": ["not in", _OPEN_TASK]})
	overdue_tasks = frappe.db.count(
		"Task",
		{**proj_in, "status": ["not in", _OPEN_TASK], "exp_end_date": ["<", str(today)]},
	)
	progress_today = len(
		frappe.get_list(
			"Task Progress Entry",
			filters={"entry_date": str(today)},
			pluck="name",
			limit_page_length=0,
		)
	)
	users = frappe.db.count("User", {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]})

	scos = frappe.get_all(
		"Scope Change Order",
		filters={**proj_in, "status": "Pending Approval"},
		fields=["name", "title", "impact"],
		order_by="modified desc",
		limit=_SCO_LIMIT,
	)
	pending_scos_ct = frappe.db.count("Scope Change Order", {**proj_in, "status": "Pending Approval"})

	# --- tasks in progress (Working), with assignee ---
	working = frappe.get_all(
		"Task",
		filters={**proj_in, "status": "Working"},
		fields=["name", "subject", "progress", "_assign", "owner"],
		order_by="modified desc",
		limit=_TASK_LIMIT,
	)
	tasks_in_progress = [
		{
			"id": t.name,
			"name": t.subject or t.name,
			"progress": flt(t.progress),
			"assignee": _first_assignee(t._assign) or t.owner,
		}
		for t in working
	]

	return {
		"kpis": {
			"active_projects": active_ct,
			"open_tasks": open_tasks,
			"overdue_tasks": overdue_tasks,
			"pending_scos": pending_scos_ct,
			"progress_today": progress_today,
			"users": users,
			"total_order_book": order_book,
		},
		"projects": projects,
		"pending_scos": [{"id": s.name, "title": s.title or s.name, "impact": flt(s.impact)} for s in scos],
		"tasks_in_progress": tasks_in_progress,
	}
