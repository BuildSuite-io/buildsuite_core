# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Whitelisted read/write for the ERPNext Project Template behind a Project
Category (one template per category, named after it). The Vue settings screen
edits a category's default Work Packages, Stages and Tasks through these — the
generic client adapter can't manage the template's native task list, which links
to is_template Tasks that must be created/updated alongside the child rows.

Only an administrator (System Manager / BuildSuite Administrator) may edit
templates, matching the Admin/BSA gate on the Project Category settings screens.
"""

import frappe
from frappe import _

from buildsuite_core.buildsuite_core.doctype.project_category.seed_project_templates import (
	_template_task,
)

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage project templates."), frappe.PermissionError)


def _template_name(project_category):
	return frappe.db.get_value("Project Template", {"project_category": project_category}, "name")


def _serialize(template):
	"""Shape a Project Template doc into the flat payload the editor expects."""
	tasks = []
	for row in template.tasks:
		tt = frappe.db.get_value(
			"Task", row.task, ["subject", "priority", "expected_time"], as_dict=True
		) or {}
		tasks.append(
			{
				"subject": tt.get("subject"),
				"priority": tt.get("priority") or "Medium",
				"hours": tt.get("expected_time") or 0,
				"work_package_code": row.get("custom_work_package_code"),
				"stage": row.get("custom_stage"),
			}
		)
	return {
		"exists": True,
		"category": template.project_category,
		"work_packages": [
			{
				"code": w.code,
				"work_package_name": w.work_package_name,
				"budget": w.budget or 0,
				"sort_order": w.sort_order or 0,
				"description": w.description,
			}
			for w in sorted(template.custom_work_packages, key=lambda r: r.sort_order or 0)
		],
		"stages": [
			{
				"stage_name": s.stage_name,
				"offset_start_days": s.offset_start_days or 0,
				"offset_end_days": s.offset_end_days or 0,
				"planned_task_count": s.planned_task_count or 0,
				"planned_completion_pct": s.planned_completion_pct or 0,
				"description": s.description,
			}
			for s in template.custom_stages
		],
		"tasks": tasks,
	}


@frappe.whitelist()
def get_project_template(project_category: str):
	"""The template behind a category — its Work Packages, Stages and Tasks (each
	task carrying the Work Package code and Stage it belongs to)."""
	_require_admin()
	if not frappe.db.exists("Project Category", project_category):
		frappe.throw(_("Unknown Project Category {0}.").format(project_category))

	name = _template_name(project_category)
	if not name:
		return {"exists": False, "category": project_category}
	return _serialize(frappe.get_doc("Project Template", name))


@frappe.whitelist()
def save_project_template(project_category: str, work_packages: str | None = None, stages: str | None = None, tasks: str | None = None):
	"""Upsert the category's template. Replaces its Work Packages, Stages and Tasks
	wholesale from the payload. Each task row becomes a fresh is_template Task; the
	previous template Tasks are removed so re-saving doesn't accumulate orphans."""
	_require_admin()
	if not frappe.db.exists("Project Category", project_category):
		frappe.throw(_("Unknown Project Category {0}.").format(project_category))

	work_packages = frappe.parse_json(work_packages) or []
	stages = frappe.parse_json(stages) or []
	tasks = frappe.parse_json(tasks) or []

	name = _template_name(project_category)
	if name:
		doc = frappe.get_doc("Project Template", name)
	else:
		doc = frappe.new_doc("Project Template")
		doc.name = project_category  # Project Template autoname is "Prompt"
		doc.project_category = project_category

	# Drop the previous is_template Tasks this template owned before rebuilding.
	old_tasks = [r.task for r in doc.tasks if r.task]

	doc.set("custom_work_packages", [])
	for w in work_packages:
		doc.append(
			"custom_work_packages",
			{
				"code": w.get("code"),
				"work_package_name": w.get("work_package_name"),
				"budget": w.get("budget") or 0,
				"sort_order": w.get("sort_order") or 0,
				"description": w.get("description"),
			},
		)

	doc.set("custom_stages", [])
	for s in stages:
		doc.append(
			"custom_stages",
			{
				"stage_name": s.get("stage_name"),
				"offset_start_days": s.get("offset_start_days") or 0,
				"offset_end_days": s.get("offset_end_days") or 0,
				"planned_task_count": s.get("planned_task_count") or 0,
				"planned_completion_pct": s.get("planned_completion_pct") or 100,
				"description": s.get("description"),
			},
		)

	doc.set("tasks", [])
	for t in tasks:
		task = _template_task(t.get("subject"), t.get("priority") or "Medium", t.get("hours") or 0)
		doc.append(
			"tasks",
			{
				"task": task.name,
				"custom_work_package_code": t.get("work_package_code"),
				"custom_stage": t.get("stage"),
			},
		)

	doc.save(ignore_permissions=True)

	for old in old_tasks:
		if frappe.db.exists("Task", old) and frappe.db.get_value("Task", old, "is_template"):
			try:
				frappe.delete_doc("Task", old, ignore_permissions=True, force=True)
			except Exception:
				frappe.log_error(frappe.get_traceback(), f"BuildSuite: prune template task {old}")

	return _serialize(frappe.get_doc("Project Template", doc.name))
