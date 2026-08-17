# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Delay Analysis report — the bespoke Site Execution report the flat Query Report can't
express. Three views over a project (and its sub-projects), each computed live:

  • Stages       — every Stage Planning: completion, slip (days past planned end while
                   incomplete) and what waits on it downstream (stages that depend on it).
  • Silent tasks — active tasks with no progress entry in the last 3 days (or ever).
  • Weekly trend — progress entries filed / completions per week over the last 6 weeks.

Stage completion reuses the Stage Planning controller's own mean_progress + task counts,
so this report and the Stage Planning screens never disagree.
"""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

SILENT_DAYS = 3
TREND_WEEKS = 6


def _scope(project):
	"""A project plus its immediate sub-projects — tasks and progress hang off the children."""
	children = frappe.get_all("Project", filters={"parent_project": project}, pluck="name")
	return [project, *children]


def _stages(project, as_of):
	stages = frappe.get_all(
		"Stage Planning",
		filters={"project": project},
		fields=[
			"name",
			"stage_name",
			"planned_start",
			"planned_end",
			"mean_progress",
			"task_count",
			"completed_task_count",
		],
		order_by="planned_start asc",
	)
	if not stages:
		return []

	label_by_name = {s.name: s.stage_name for s in stages}
	# A dependency row lives on the stage that HAS the dependency and points (`stage`) at the
	# stage it waits on. So for each dependency, the pointed-at stage's downstream gains the
	# owning (parent) stage.
	downstream = {}
	for d in frappe.get_all(
		"Stage Planning Dependency",
		filters={"parent": ["in", list(label_by_name)]},
		fields=["parent", "stage"],
	):
		if d.stage:
			downstream.setdefault(d.stage, []).append(label_by_name.get(d.parent, d.parent))

	out = []
	for s in stages:
		pct = round(flt(s.mean_progress)) if s.task_count else None
		end = getdate(s.planned_end) if s.planned_end else None
		overdue = (as_of - end).days if (end and end < as_of and (pct is None or pct < 100)) else 0
		out.append(
			{
				"name": s.name,
				"stage_name": s.stage_name,
				"planned_start": str(s.planned_start) if s.planned_start else None,
				"planned_end": str(s.planned_end) if s.planned_end else None,
				"pct": pct,
				"task_count": s.task_count or 0,
				"done_count": s.completed_task_count or 0,
				"overdue": overdue,
				"downstream": downstream.get(s.name, []),
			}
		)
	out.sort(key=lambda r: (-r["overdue"], r["planned_start"] or ""))
	return out


def _silent_tasks(project, as_of):
	tasks = frappe.get_all(
		"Task",
		filters={
			"project": ["in", _scope(project)],
			"is_group": 0,
			"task_status": ["not in", ["Completed", "Yet To Start"]],
		},
		fields=["name", "subject", "task_status"],
	)
	if not tasks:
		return []

	last_by_task = {
		r.task: r.last
		for r in frappe.db.sql(
			"""SELECT task, MAX(entry_date) AS last FROM `tabTask Progress Entry`
			WHERE task IN %(tasks)s GROUP BY task""",
			{"tasks": [t.name for t in tasks]},
			as_dict=True,
		)
	}
	out = []
	for t in tasks:
		last = last_by_task.get(t.name)
		days = (as_of - getdate(last)).days if last else None
		if days is None or days >= SILENT_DAYS:
			out.append(
				{
					"task": t.name,
					"subject": t.subject,
					"status": t.task_status,
					"last": str(last) if last else None,
					"days": days,
				}
			)
	out.sort(key=lambda r: r["days"] if r["days"] is not None else 9999, reverse=True)
	return out


def _weekly_trend(project, as_of):
	tasks = frappe.get_all("Task", filters={"project": ["in", _scope(project)]}, pluck="name")
	weeks = []
	for i in range(TREND_WEEKS - 1, -1, -1):
		end = add_days(as_of, -i * 7)
		start = add_days(end, -6)
		entries = (
			frappe.get_all(
				"Task Progress Entry",
				filters={"task": ["in", tasks], "entry_date": ["between", [start, end]]},
				fields=["cumulative_progress"],
			)
			if tasks
			else []
		)
		completed = sum(1 for e in entries if flt(e.cumulative_progress) >= 100)
		weeks.append({"label": str(start), "entries": len(entries), "completed": completed})
	mx = max([1, *[w["entries"] for w in weeks]])
	for w in weeks:
		w["pct"] = (w["entries"] / mx) * 100
	return weeks


@frappe.whitelist()
def delay_analysis(project=None):
	"""The three Delay Analysis views for a project. Empty payload when no project is given."""
	if not project:
		return {"stages": [], "silent_tasks": [], "weekly_trend": []}
	as_of = getdate(nowdate())
	return {
		"stages": _stages(project, as_of),
		"silent_tasks": _silent_tasks(project, as_of),
		"weekly_trend": _weekly_trend(project, as_of),
	}
