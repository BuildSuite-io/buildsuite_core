# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Backfill `company` on existing rows after the multi-company rollout.

Project-scoped doctypes that gained a `company` field inherit it from their project (Task
Progress Entry via task → project). Catalog masters that became per-company are stamped with
the default company — they were created under it; duplicate per company later if needed.
"""

import frappe

from buildsuite_core.utils.project import default_company

# doctype -> field holding the Project link
_PROJECT_SCOPED = {
	"Work Package": "project",
	"Stage Planning": "project",
	"Field Attendance": "project",
	"Machinery Usage": "project",
	"Schedule Snapshot": "project",
	"BOQ": "project",
	"Measurement Book": "project",
	"Scope Change Order": "project",
}

_MASTERS = (
	"Assembly",
	"Assembly Category",
	"Construction Rate Master",
	"Rate Master Category",
	"Estimate Template",
	"Project Category",
	"Machinery Type",
	"Subcontract Delivery Type",
	"Construction Trade",
	"Labour Trade",
	# Org-wide ERPNext masters made company-scoped — stamp existing rows to the default company.
	"Supplier",
	"Customer",
	"Item",
)


def _needs_company(dt, extra_fields):
	# Rows where company is not yet set. New Link fields default to NULL.
	return frappe.get_all(
		dt, filters={"company": ["is", "not set"]}, fields=["name", *extra_fields]
	)


def execute():
	skipped = {}  # doctype -> count of rows left company-less (project/task has no company)

	# Project-scoped: company from the linked project.
	for dt, project_field in _PROJECT_SCOPED.items():
		if not frappe.db.has_column(dt, "company"):
			continue
		for row in _needs_company(dt, [project_field]):
			project = row.get(project_field)
			company = frappe.db.get_value("Project", project, "company") if project else None
			if company:
				frappe.db.set_value(dt, row.name, "company", company, update_modified=False)
			else:
				skipped[dt] = skipped.get(dt, 0) + 1

	# Task Progress Entry: company via task -> project.
	if frappe.db.has_column("Task Progress Entry", "company"):
		for row in _needs_company("Task Progress Entry", ["task"]):
			project = frappe.db.get_value("Task", row.task, "project") if row.task else None
			company = frappe.db.get_value("Project", project, "company") if project else None
			if company:
				frappe.db.set_value(
					"Task Progress Entry", row.name, "company", company, update_modified=False
				)
			else:
				skipped["Task Progress Entry"] = skipped.get("Task Progress Entry", 0) + 1

	# Catalog masters: stamp the default company on any unassigned rows.
	default = default_company()
	if default:
		for dt in _MASTERS:
			if not frappe.db.has_column(dt, "company"):
				continue
			for name in frappe.get_all(dt, filters={"company": ["is", "not set"]}, pluck="name"):
				frappe.db.set_value(dt, name, "company", default, update_modified=False)

	# Surface rows we could not stamp — their project/task has no company, so they stay
	# company-less. Cross-company guards no-op on a NULL company, so these are worth flagging
	# rather than leaving silent.
	if skipped:
		summary = ", ".join(f"{n} {dt}" for dt, n in skipped.items())
		msg = f"Left company unset on rows whose project has no company: {summary}."
		print(f"backfill_company_scope: {msg}")
		frappe.log_error(msg, "Multi-company backfill")
