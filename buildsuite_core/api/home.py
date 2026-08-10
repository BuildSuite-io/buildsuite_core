# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Home dashboard — the role-aware snapshot backing AppHomeView (`/home`), plus the legacy
fields the denser Desk overview (`/dashboard`) still renders.

One aggregate read. It resolves the logged-in user's role (their Persona) and returns that
role's four snapshot tiles, a primary CTA, and three alert cards — the same per-role content
as the prototype's HomeWorkspaceView. All project/task/SCO reads go through get_list, so the
permission query conditions apply: a team-scoped user (QS, Site Engineer, …) sees only their
own projects/tasks; admins/PMs see the whole company. Single-company for now."""

import json

import frappe
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

from buildsuite_core.utils.project import default_company

_ACTIVE = ("New", "Ongoing", "Delayed")
_BOQ_RANK = {"Approved": 2, "Submitted": 1}
_PROJECT_LIMIT = 12
_TASK_LIMIT = 6
_SCO_LIMIT = 8
_OPEN_TASK = ("Completed", "Cancelled", "Template")

# Roles that see the whole company (no team scoping) — mirrors permissions._is_scoped.
_ADMIN_ROLES = ("admin", "bsa")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _count(doctype, filters):
	"""Company/project-scoped count that never raises (a missing doctype/field → 0)."""
	try:
		return frappe.db.count(doctype, filters)
	except Exception:
		return 0


def _sum(doctype, filters, field):
	try:
		rows = frappe.get_all(doctype, filters=filters, fields=[f"sum(`{field}`) as t"])
		return flt(rows[0].t) if rows else 0.0
	except Exception:
		return 0.0


def _current_boq(project_names):
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
	if not start or not end:
		return 0.0
	span = date_diff(end, start)
	if span <= 0:
		return 0.0
	return max(0.0, min(100.0, date_diff(today, start) / span * 100.0))


def _tone(expected, progress):
	if expected <= 0:
		return "success"
	variance = (expected - progress) / expected * 100.0
	if variance > 15:
		return "danger"
	if variance > 5:
		return "warning"
	return "success"


def _first_assignee(assign):
	if not assign:
		return None
	try:
		users = json.loads(assign)
		return users[0] if users else None
	except (ValueError, TypeError):
		return None


def _resolve_role(user):
	"""The user's BuildSuite role id (Persona.slug), e.g. 'qs'. Falls back to 'admin' for a
	System Manager / no persona so they get the org-wide snapshot."""
	persona = frappe.db.get_value("User", user, "persona") if user else None
	role = frappe.db.get_value("Persona", persona, "slug") if persona else None
	if role:
		return role
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles:
		return "admin"
	return "site-engineer"


def _cash_and_bank(company):
	from erpnext.accounts.utils import get_balance_on

	total = 0.0
	for a in frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		pluck="name",
	):
		try:
			total += flt(get_balance_on(account=a, company=company))
		except Exception:
			pass
	return total


# --------------------------------------------------------------------------- #
# snapshot / CTA / alerts — per role
# --------------------------------------------------------------------------- #
def _tile(label, value, slug, tone="brand", fmt="int"):
	return {"label": label, "value": value, "slug": slug, "tone": tone, "format": fmt}


def _alert(key, title, value, sub, slug, to, active, tone="warning"):
	return {
		"key": key,
		"title": title,
		"value": value,
		"sub": sub,
		"slug": slug,
		"to": to,
		"tone": tone if active else "muted",
	}


_GREETINGS = {
	"admin": "Here is a snapshot of system activity today.",
	"bsa": "Here is a snapshot of system activity today.",
	"director": "Here is where your portfolio stands today.",
	"pm": "Here is what needs your attention across your projects.",
	"accountant": "Here is the money position and today's queues.",
	"estimator": "Here is a summary of your estimation work today.",
	"qs": "Here is a summary of your estimation and measurement work today.",
	"site-engineer": "Here is your work on site today.",
	"foreman": "Here is your crew and work on site today.",
	"procurement": "Here is the buying pipeline today.",
	"store-keeper": "Here is the store and deliveries today.",
	"hr-manager": "Here is the workforce position today.",
}

# CTA per role — (title, sub, cta-label, route, icon slug).
_CTAS = {
	"admin": (
		"Settings",
		"Manage workspaces, users, project types, and data.",
		"Open Settings",
		"/settings",
		"settings",
	),
	"bsa": (
		"Settings",
		"Manage workspaces, users, project types, and data.",
		"Open Settings",
		"/settings",
		"settings",
	),
	"director": (
		"Project Dashboard",
		"Portfolio health, risks, and high-value approvals.",
		"Open",
		"/project-dashboard",
		"chart-bar",
	),
	"pm": (
		"Project Dashboard",
		"Portfolio health, risks, and high-value approvals.",
		"Open",
		"/project-dashboard",
		"chart-bar",
	),
	"accountant": (
		"Project Finance",
		"Cash position, receivables, payables and the day's queues.",
		"Open",
		"/project-finance",
		"wallet",
	),
	"estimator": (
		"BOQ Workbench",
		"Bill of quantities register, templates and revision compare.",
		"Open",
		"/boq",
		"estimation",
	),
	"qs": (
		"Measurement Books",
		"Certify site measurements — certified MBs drive subcontractor bills.",
		"Open",
		"/measurement-books",
		"clipboard-list",
	),
	"site-engineer": (
		"File progress entry",
		"Report today's progress, labour and any blockers.",
		"Open",
		"/progress-entries/new",
		"file-text",
	),
	"foreman": (
		"Mark attendance",
		"Log the crew for today — wages and labour cost derive from it.",
		"Open",
		"/workforce",
		"users",
	),
	"procurement": (
		"Procurement Dashboard",
		"Open requests, on-order value, receipts and rate variances.",
		"Open",
		"/procurement-dashboard",
		"chart-bar",
	),
	"store-keeper": (
		"Procurement",
		"Confirm deliveries against their purchase orders.",
		"Open",
		"/procurement",
		"stock",
	),
	"hr-manager": (
		"Workforce",
		"Man-days, labour cost and attendance across projects.",
		"Open",
		"/workforce",
		"workforce",
	),
}


@frappe.whitelist()
def get_home_dashboard():
	user = frappe.session.user
	company = default_company()
	role = _resolve_role(user)
	today = getdate(nowdate())
	week_ago = str(add_days(today, -7))

	# --- scoped project set (permission query conditions apply via get_list) ---
	project_ids = frappe.get_list(
		"Project", filters={"company": company}, pluck="name", limit_page_length=0
	) or ["__none__"]
	proj_in = {"project": ["in", project_ids]}

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

	projects, order_book, active_ct, at_risk = [], 0.0, 0, 0
	for p in roots:
		if not (p.project_status in _ACTIVE and p.status != "Cancelled"):
			continue
		active_ct += 1
		planned = boq.get(p.name, flt(p.estimated_costing))
		order_book += flt(planned)
		progress = flt(p.percent_complete)
		expected = _expected_pct(today, p.expected_start_date, p.expected_end_date)
		if _tone(expected, progress) == "danger":
			at_risk += 1
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

	# --- common counts (scoped) ---
	open_tasks = _count("Task", {**proj_in, "status": ["not in", _OPEN_TASK]})
	overdue_tasks = _count(
		"Task", {**proj_in, "status": ["not in", _OPEN_TASK], "exp_end_date": ["<", str(today)]}
	)
	progress_today = len(
		frappe.get_list(
			"Task Progress Entry", filters={"entry_date": str(today)}, pluck="name", limit_page_length=0
		)
	)
	users = _count("User", {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]})
	stage_pending = _count("Stage Planning", {**proj_in, "workflow_state": "Pending Approval"})
	pending_scos_ct = _count("Scope Change Order", {**proj_in, "status": "Pending Approval"})

	scos = frappe.get_all(
		"Scope Change Order",
		filters={**proj_in, "status": "Pending Approval"},
		fields=["name", "title", "impact"],
		order_by="modified desc",
		limit=_SCO_LIMIT,
	)
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

	# --- my-task metrics (field roles) ---
	def _my(extra=None):
		f = {**proj_in, "status": ["not in", _OPEN_TASK], "_assign": ["like", f"%{user}%"]}
		if extra:
			f.update(extra)
		return _count("Task", f)

	my_open = _my()
	my_overdue = _my({"exp_end_date": ["<", str(today)]})
	my_due_week = _my({"exp_end_date": ["between", [str(today), str(add_days(today, 7))]]})
	my_progress_today = len(
		frappe.get_list(
			"Task Progress Entry",
			filters={"entry_date": str(today), "owner": user},
			pluck="name",
			limit_page_length=0,
		)
	)

	# --- lazily-computed heavier metrics (only used by some roles) ---
	def boqs():
		return _count("BOQ", {**proj_in, "status": "Draft"}), _count("BOQ", {**proj_in, "status": "Approved"})

	def finance():
		recv = _sum("Sales Invoice", {"company": company, "docstatus": 1}, "outstanding_amount")
		pay = _sum("Purchase Invoice", {"company": company, "docstatus": 1}, "outstanding_amount")
		overdue_recv = _count(
			"Sales Invoice",
			{
				"company": company,
				"docstatus": 1,
				"outstanding_amount": [">", 0],
				"due_date": ["<", str(today)],
			},
		)
		return recv, pay, overdue_recv

	def procurement():
		on_order = _sum(
			"Purchase Order",
			{
				**proj_in,
				"docstatus": 1,
				"status": ["not in", ["Closed", "Cancelled"]],
				"per_received": ["<", 100],
			},
			"grand_total",
		)
		on_order_ct = _count(
			"Purchase Order",
			{
				**proj_in,
				"docstatus": 1,
				"status": ["not in", ["Closed", "Cancelled"]],
				"per_received": ["<", 100],
			},
		)
		overdue_del = _count(
			"Purchase Order",
			{**proj_in, "docstatus": 1, "per_received": ["<", 100], "schedule_date": ["<", str(today)]},
		)
		mrs_pending = _count("Material Request", {**proj_in, "docstatus": 0})
		received_week = _count(
			"Purchase Receipt", {**proj_in, "docstatus": 1, "posting_date": [">=", week_ago]}
		)
		return on_order, on_order_ct, overdue_del, mrs_pending, received_week

	# --- role → snapshot + alerts ---
	stage_alert = _alert(
		"stages",
		"Stage approvals pending",
		stage_pending,
		f"{stage_pending} awaiting your approval" if stage_pending else "No stages waiting",
		"check-circle",
		"/stage-plannings?status=Pending Approval",
		stage_pending > 0,
	)
	sco_alert = _alert(
		"sco",
		"Pending SCOs",
		pending_scos_ct,
		f"{pending_scos_ct} awaiting approval" if pending_scos_ct else "No scope changes waiting",
		"refresh-ccw",
		"/sco",
		pending_scos_ct > 0,
	)

	if role in _ADMIN_ROLES:
		snapshot = [
			_tile("Active projects", active_ct, "clipboard-list"),
			_tile("Open tasks", open_tasks, "check-circle", "info"),
			_tile("Users", users, "users", "success"),
			_tile(
				"Pending stage approvals",
				stage_pending,
				"check-circle",
				"warning" if stage_pending else "brand",
			),
		]
		alerts = [
			stage_alert,
			sco_alert,
			_alert(
				"overdue",
				"Overdue tasks",
				overdue_tasks,
				f"{overdue_tasks} past their end date" if overdue_tasks else "Nothing overdue",
				"refresh-ccw",
				"/tasks?status=overdue",
				overdue_tasks > 0,
				"danger",
			),
		]
	elif role == "director":
		recv, pay, overdue_recv = finance()
		snapshot = [
			_tile("Active projects", active_ct, "clipboard-list"),
			_tile("Projects at risk", at_risk, "chart-line", "danger" if at_risk else "success"),
			_tile("Receivables", recv, "banknote", "info", "currency"),
			_tile("Payables", pay, "receipt", "warning", "currency"),
		]
		alerts = [
			stage_alert,
			sco_alert,
			_alert(
				"recv",
				"Overdue receivables",
				overdue_recv,
				f"{overdue_recv} invoice(s) past due" if overdue_recv else "No customer invoices past due",
				"banknote",
				"/project-finance",
				overdue_recv > 0,
				"danger",
			),
		]
	elif role == "pm":
		on_order, on_order_ct, overdue_del, mrs_pending, _rw = procurement()
		snapshot = [
			_tile("Active projects", active_ct, "clipboard-list"),
			_tile("Open tasks", open_tasks, "check-circle", "info"),
			_tile(
				"Stage approvals", stage_pending, "check-circle", "warning" if stage_pending else "success"
			),
			_tile("MRs awaiting approval", mrs_pending, "procurement", "warning" if mrs_pending else "muted"),
		]
		alerts = [
			stage_alert,
			_alert(
				"mrs",
				"MRs awaiting approval",
				mrs_pending,
				f"{mrs_pending} request(s) to review" if mrs_pending else "No requests waiting",
				"procurement",
				"/procurement/material-requests",
				mrs_pending > 0,
			),
			_alert(
				"overdue-del",
				"Overdue deliveries",
				overdue_del,
				f"{overdue_del} PO(s) past required-by" if overdue_del else "Supply is on schedule",
				"refresh-ccw",
				"/procurement/purchase-orders",
				overdue_del > 0,
				"danger",
			),
		]
	elif role == "accountant":
		recv, pay, overdue_recv = finance()
		cash = _cash_and_bank(company)
		to_verify = _count("Expense Entry", {"company": company, "docstatus": 0})
		petty = _count("Petty Cash Request", {"company": company, "status": "Requested"})
		snapshot = [
			_tile("Cash & bank", cash, "wallet", "brand", "currency"),
			_tile("Receivables", recv, "banknote", "info", "currency"),
			_tile("Payables", pay, "receipt", "warning", "currency"),
			_tile("Expenses to verify", to_verify, "file-text", "danger" if to_verify else "success"),
		]
		alerts = [
			_alert(
				"exp",
				"Expenses to verify",
				to_verify,
				f"{to_verify} draft expense(s) to submit" if to_verify else "Verification queue is clear",
				"file-text",
				"/project-finance/expenses",
				to_verify > 0,
				"danger",
			),
			_alert(
				"petty",
				"Petty cash to disburse",
				petty,
				f"{petty} request(s) to disburse" if petty else "No requests waiting",
				"wallet",
				"/project-finance/petty-cash",
				petty > 0,
			),
			_alert(
				"recv",
				"Overdue receivables",
				overdue_recv,
				f"{overdue_recv} invoice(s) past due" if overdue_recv else "No customer invoices past due",
				"banknote",
				"/project-finance",
				overdue_recv > 0,
				"danger",
			),
		]
	elif role == "estimator":
		draft_boqs, approved_boqs = boqs()
		templates = _count("Estimate Template", {})
		assemblies = _count("Assembly", {})
		snapshot = [
			_tile("Draft BOQs", draft_boqs, "file-text", "warning"),
			_tile("Approved BOQs", approved_boqs, "check-circle", "success"),
			_tile("Estimate templates", templates, "layout-grid", "info"),
			_tile("Assemblies", assemblies, "chart-bar"),
		]
		alerts = [
			_alert(
				"drafts",
				"Draft BOQs",
				draft_boqs,
				f"{draft_boqs} open" if draft_boqs else "No drafts in flight",
				"file-text",
				"/boq",
				draft_boqs > 0,
				"info",
			),
			_alert(
				"templates",
				"Estimate templates",
				templates,
				f"{templates} configured",
				"layout-grid",
				"/estimation",
				templates > 0,
				"info",
			),
			_alert(
				"assemblies",
				"Assemblies",
				assemblies,
				f"{assemblies} in the library",
				"chart-bar",
				"/assembly",
				assemblies > 0,
				"info",
			),
		]
	elif role == "qs":
		draft_boqs, approved_boqs = boqs()
		mbs = _count("Measurement Book", {"company": company, "status": "Draft"})
		snapshot = [
			_tile("Draft BOQs", draft_boqs, "file-text", "warning"),
			_tile("Approved BOQs", approved_boqs, "check-circle", "success"),
			_tile("MBs to certify", mbs, "clipboard-list", "danger" if mbs else "muted"),
			_tile("Active projects", active_ct, "building-2"),
		]
		alerts = [
			_alert(
				"mbs",
				"MBs to certify",
				mbs,
				f"{mbs} awaiting certification" if mbs else "No draft measurement books",
				"clipboard-list",
				"/measurement-books",
				mbs > 0,
				"danger",
			),
			_alert(
				"drafts",
				"Draft BOQs",
				draft_boqs,
				f"{draft_boqs} open" if draft_boqs else "No drafts in flight",
				"file-text",
				"/boq",
				draft_boqs > 0,
				"info",
			),
			sco_alert,
		]
	elif role == "procurement":
		on_order, on_order_ct, overdue_del, mrs_pending, received_week = procurement()
		snapshot = [
			_tile("MRs to approve", mrs_pending, "clipboard-list", "warning" if mrs_pending else "muted"),
			_tile("Received this week", received_week, "check-circle", "success"),
			_tile("On order", on_order, "procurement", "brand", "currency"),
			_tile("Overdue deliveries", overdue_del, "refresh-ccw", "danger" if overdue_del else "success"),
		]
		alerts = [
			_alert(
				"overdue-del",
				"Overdue deliveries",
				overdue_del,
				f"{overdue_del} PO(s) past required-by" if overdue_del else "Supply is on schedule",
				"refresh-ccw",
				"/procurement/purchase-orders",
				overdue_del > 0,
				"danger",
			),
			_alert(
				"mrs",
				"MRs to approve",
				mrs_pending,
				f"{mrs_pending} request(s) to review" if mrs_pending else "No requests waiting",
				"clipboard-list",
				"/procurement/material-requests",
				mrs_pending > 0,
			),
			_alert(
				"on-order",
				"On order",
				on_order_ct,
				f"{on_order_ct} PO(s) awaiting delivery" if on_order_ct else "Nothing on order",
				"procurement",
				"/procurement/purchase-orders",
				on_order_ct > 0,
				"info",
			),
		]
	elif role == "store-keeper":
		on_order, on_order_ct, overdue_del, _mp, received_week = procurement()
		snapshot = [
			_tile("Deliveries open", on_order_ct, "procurement"),
			_tile("Received this week", received_week, "stock", "success"),
			_tile("Overdue deliveries", overdue_del, "refresh-ccw", "danger" if overdue_del else "muted"),
			_tile("Active projects", active_ct, "building-2", "info"),
		]
		alerts = [
			_alert(
				"overdue-del",
				"Overdue deliveries",
				overdue_del,
				f"{overdue_del} PO(s) past required-by" if overdue_del else "Nothing overdue on the way",
				"refresh-ccw",
				"/procurement/purchase-orders",
				overdue_del > 0,
				"danger",
			),
			_alert(
				"open-del",
				"Deliveries open",
				on_order_ct,
				f"{on_order_ct} awaiting receipt" if on_order_ct else "No open deliveries",
				"procurement",
				"/procurement/purchase-orders",
				on_order_ct > 0,
			),
			_alert(
				"received",
				"Received this week",
				received_week,
				f"{received_week} receipt(s) booked" if received_week else "Nothing received yet",
				"stock",
				"/procurement/receipts",
				received_week > 0,
				"success",
			),
		]
	elif role == "foreman":
		att_today = _count(
			"Field Attendance", {"company": company, "date": str(today), "docstatus": ["<", 2]}
		)
		snapshot = [
			_tile("Attendance today", att_today, "users", "success" if att_today else "warning"),
			_tile("My open tasks", my_open, "check-circle"),
			_tile("Overdue", my_overdue, "refresh-ccw", "danger" if my_overdue else "muted"),
			_tile(
				"Progress today",
				my_progress_today,
				"file-text",
				"success" if my_progress_today else "warning",
			),
		]
		alerts = [
			_alert(
				"att",
				"Attendance today",
				att_today,
				f"{att_today} sheet(s) marked" if att_today else "Not marked yet — mark it before noon",
				"users",
				"/workforce",
				att_today > 0,
				"success",
			),
			_alert(
				"overdue",
				"My overdue tasks",
				my_overdue,
				f"{my_overdue} past their end date" if my_overdue else "On track — nothing past due",
				"refresh-ccw",
				"/tasks",
				my_overdue > 0,
				"danger",
			),
			_alert(
				"progress",
				"Progress today",
				my_progress_today,
				f"{my_progress_today} filed today" if my_progress_today else "No entries filed yet",
				"file-text",
				"/progress-entries",
				my_progress_today > 0,
				"success",
			),
		]
	elif role == "hr-manager":
		att_week = _count("Field Attendance", {"company": company, "docstatus": 1, "date": [">=", week_ago]})
		ot_hours = _sum("Overtime Attendance Register", {"company": company}, "overtime_hours")
		workers = _count("Employee", {"status": "Active"})
		snapshot = [
			_tile("Active workers", workers, "users", "brand"),
			_tile("Attendance this week", att_week, "check-circle", "success" if att_week else "muted"),
			_tile("Overtime (hrs) this week", round(ot_hours), "calendar", "info"),
			_tile("Active projects", active_ct, "building-2"),
		]
		alerts = [
			_alert(
				"att-week",
				"Attendance this week",
				att_week,
				f"{att_week} sheet(s) submitted" if att_week else "No sheets submitted yet",
				"check-circle",
				"/workforce",
				att_week > 0,
				"success",
			),
			_alert(
				"ot",
				"Overtime this week",
				round(ot_hours),
				f"{round(ot_hours)} hrs across the crews" if ot_hours else "No overtime recorded",
				"calendar",
				"/workforce",
				ot_hours > 0,
			),
			_alert(
				"workers",
				"Active workers",
				workers,
				f"{workers} on the books",
				"users",
				"/workforce",
				workers > 0,
				"info",
			),
		]
	else:  # site-engineer + any unmapped role
		snapshot = [
			_tile("My open tasks", my_open, "check-circle"),
			_tile("Due this week", my_due_week, "calendar", "info"),
			_tile("Overdue", my_overdue, "refresh-ccw", "danger" if my_overdue else "muted"),
			_tile(
				"Progress today",
				my_progress_today,
				"file-text",
				"success" if my_progress_today else "warning",
			),
		]
		on_order, on_order_ct, overdue_del, _mp, _rw = procurement()
		alerts = [
			_alert(
				"overdue",
				"My overdue tasks",
				my_overdue,
				f"{my_overdue} past their end date" if my_overdue else "On track — nothing past due",
				"refresh-ccw",
				"/tasks",
				my_overdue > 0,
				"danger",
			),
			_alert(
				"deliveries",
				"Deliveries expected",
				overdue_del,
				f"{overdue_del} PO(s) past required-by" if overdue_del else "Nothing overdue on the way",
				"procurement",
				"/procurement/purchase-orders",
				overdue_del > 0,
			),
			_alert(
				"progress",
				"Progress today",
				my_progress_today,
				f"{my_progress_today} filed today" if my_progress_today else "No entries filed yet",
				"file-text",
				"/progress-entries",
				my_progress_today > 0,
				"success",
			),
		]

	title, sub, cta_label, to, cta_slug = _CTAS.get(role, _CTAS["site-engineer"])
	cta = {"title": title, "sub": sub, "cta": cta_label, "to": to, "slug": cta_slug}

	return {
		"role": role,
		"greeting_sub": _GREETINGS.get(role, "Here is a snapshot of your work today."),
		"snapshot": snapshot,
		"cta": cta,
		"alerts": alerts,
		# --- legacy fields still rendered by DashboardView (/dashboard) ---
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
