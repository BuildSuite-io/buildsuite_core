# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Labour Cost Summary - hours, man-days and what labour cost, by project, cost code or worker.

Built on `utils.labour_cost.labour_cost_rows`, the one reader of the Labour and Overtime Attendance
Registers, where submitted attendance and submitted timesheets both write. Nothing here reads a
sheet or a timesheet except to count the drafts for the footer.

  Hours         regular hours only; overtime is always separate (OT hrs)
  Man-days      each row's regular hours over the full day kept on it, added up
  Regular cost  the Labour register's wage; OT cost the Overtime register's
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from buildsuite_core.report_access import is_route_permitted
from buildsuite_core.utils.labour_cost import labour_cost_rows
from buildsuite_core.utils.project import company_scope

ROUTE = "/workforce/labour-cost-summary"
GROUPS = ("project", "code", "worker")
SOURCES = ("Attendance", "Timesheet")


@frappe.whitelist()
def get_summary(
	project: str | None = None,
	worker: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
	source: str | None = None,
	group_by: str = "project",
) -> dict:
	if not is_route_permitted(ROUTE):
		frappe.throw(_("You are not permitted to open the Labour Cost Summary."), frappe.PermissionError)
	group_by = group_by if group_by in GROUPS else "project"
	source = source if source in SOURCES else None

	readable = frappe.get_list(
		"Project",
		filters={"company": company_scope()} if company_scope() else {},
		pluck="name",
		limit_page_length=0,
	)
	# The filter options are what the registers hold on projects this user can read, whatever the
	# other filters say.
	all_lines = labour_cost_rows({"projects": readable})
	filters = {
		"projects": [project] if project and project in readable else ([] if project else readable),
		"worker": worker,
		"from": from_date,
		"to": to_date,
		"source": source,
	}
	lines = labour_cost_rows(filters)
	names = _names(all_lines)

	return {
		"group_by": group_by,
		"rows": summarise(lines, group_by, names),
		"totals": grand_total(lines),
		"period": _period(lines),
		"drafts": count_drafts(filters),
		"projects": [
			{
				"value": p,
				"label": names["project"].get(p, (p, p))[0],
				"hint": names["project"].get(p, (p, p))[1],
			}
			for p in sorted({r["project"] for r in all_lines if r["project"]})
		],
		"workers": [
			{
				"value": w,
				"label": names["worker"].get(w, (w, ""))[0],
				"hint": names["worker"].get(w, (w, ""))[1],
			}
			for w in sorted({r["employee"] for r in all_lines if r["employee"]})
		],
	}


def _names(lines) -> dict:
	"""project -> (name, id), worker -> (name, trade), for what the lines mention."""
	projects = {r["project"] for r in lines if r["project"]}
	workers = {r["employee"] for r in lines if r["employee"]}
	proj = {
		p.name: (p.project_name or p.name, p.custom_project_id or p.name)
		for p in frappe.get_all(
			"Project",
			filters={"name": ["in", list(projects) or [""]]},
			fields=["name", "project_name", "custom_project_id"],
		)
	}
	work = {
		e.name: (e.employee_name or e.name, e.custom_trade or "")
		for e in frappe.get_all(
			"Employee",
			filters={"name": ["in", list(workers) or [""]]},
			fields=["name", "employee_name", "custom_trade"],
		)
	}
	return {"project": proj, "worker": work}


def _worked(r) -> bool:
	"""A day worked has regular hours or overtime; an absence adds nothing."""
	return bool(r["date"]) and (flt(r["regular_hours"]) > 0 or flt(r["ot_hours"]) > 0)


def _code(cost_code) -> str:
	return (cost_code or {}).get("item_code") or (cost_code or {}).get("group_code") or ""


def _code_text(cost_code) -> str:
	parts = str((cost_code or {}).get("label") or "").split(" · ")
	return " · ".join(parts[1:]) if len(parts) > 1 else ""


def _bucket(r, group_by, names) -> dict:
	if group_by == "worker":
		label, sub = names["worker"].get(r["employee"], (r["employee_name"], ""))
		return {"key": r["employee"], "label": label, "sub": sub}
	if group_by == "code":
		code = _code(r["cost_code"])
		project = r["project"]
		if code:
			return {
				"key": f"{project}|{code}",
				"label": code,
				"sub": _code_text(r["cost_code"]),
				"project": project,
				"project_label": names["project"].get(project, (project, project))[0],
			}
		return {
			"key": f"{project}|",
			"label": _("No cost code"),
			"sub": "",
			"project": project,
			"project_label": names["project"].get(project, (project, project))[0],
			"uncoded": True,
		}
	label, sub = names["project"].get(r["project"], (r["project"], r["project"]))
	return {"key": r["project"], "label": label, "sub": sub}


def _share(ot, total) -> float:
	return (flt(ot) / flt(total) * 100) if flt(total) > 0 else 0.0


def summarise(lines, group_by, names) -> list[dict]:
	by: dict = {}
	for r in lines:
		head = _bucket(r, group_by, names)
		b = by.setdefault(
			head["key"],
			{**head, "_workers": set(), "_projects": set(), "_dates": set()}
			| dict.fromkeys(("hours", "man_days", "regular_cost", "ot_hours", "ot_cost"), 0.0),
		)
		b["_workers"].add(r["employee"])
		b["_projects"].add(r["project"])
		if _worked(r):
			b["_dates"].add(r["date"])
		b["hours"] += flt(r["regular_hours"])
		b["man_days"] += flt(r["man_days"])
		b["regular_cost"] += flt(r["regular_cost"])
		b["ot_hours"] += flt(r["ot_hours"])
		b["ot_cost"] += flt(r["ot_cost"])

	out = []
	for b in by.values():
		total = b["regular_cost"] + b["ot_cost"]
		out.append(
			{
				**{k: v for k, v in b.items() if not k.startswith("_")},
				"workers": len(b["_workers"]),
				"projects": len(b["_projects"]),
				"days_worked": len(b["_dates"]),
				"total": total,
				"ot_share": _share(b["ot_cost"], total),
			}
		)
	out.sort(key=lambda x: (-x["total"], str(x["label"])))
	return out


def grand_total(lines) -> dict:
	"""Distinct across the whole set: someone on two projects is one worker."""
	regular = sum(flt(r["regular_cost"]) for r in lines)
	ot = sum(flt(r["ot_cost"]) for r in lines)
	return {
		"workers": len({r["employee"] for r in lines}),
		"projects": len({r["project"] for r in lines}),
		"days_worked": len({r["date"] for r in lines if _worked(r)}),
		"hours": sum(flt(r["regular_hours"]) for r in lines),
		"man_days": sum(flt(r["man_days"]) for r in lines),
		"regular_cost": regular,
		"ot_hours": sum(flt(r["ot_hours"]) for r in lines),
		"ot_cost": ot,
		"total": regular + ot,
		"ot_share": _share(ot, regular + ot),
	}


def _period(lines) -> dict:
	dates = sorted(str(r["date"]) for r in lines if r["date"])
	return {"from": dates[0], "to": dates[-1]} if dates else {}


def count_drafts(filters: dict) -> int:
	"""Draft Field Attendance sheets and Timesheets inside the same filters: entries that are not
	counted yet because they are not submitted."""
	projects = filters.get("projects")
	if projects is not None and not projects:
		return 0
	source, worker = filters.get("source"), filters.get("worker")
	start, end = filters.get("from"), filters.get("to")
	count = 0

	if source != "Timesheet":
		sheet_filters: list = [["docstatus", "=", 0]]
		if projects is not None:
			sheet_filters.append(["project", "in", projects])
		if start:
			sheet_filters.append(["date", ">=", getdate(start)])
		if end:
			sheet_filters.append(["date", "<=", getdate(end)])
		sheets = frappe.get_all("Field Attendance", filters=sheet_filters, pluck="name")
		if worker and sheets:
			sheets = frappe.get_all(
				"Field Attendance Employee",
				filters={"parent": ["in", sheets], "employee": worker},
				pluck="parent",
			)
		count += len(set(sheets))

	if source != "Attendance":
		row_filters: list = [["parenttype", "=", "Timesheet"], ["docstatus", "=", 0]]
		if projects is not None:
			row_filters.append(["project", "in", projects])
		if start:
			row_filters.append(["from_time", ">=", getdate(start)])
		if end:
			row_filters.append(["from_time", "<", add_days(getdate(end), 1)])
		parents = set(frappe.get_all("Timesheet Detail", filters=row_filters, pluck="parent"))
		if worker and parents:
			parents = set(
				frappe.get_all(
					"Timesheet", filters={"name": ["in", list(parents)], "employee": worker}, pluck="name"
				)
			)
		count += len(parents)
	return count
