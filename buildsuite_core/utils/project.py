import frappe
from frappe import _
from frappe.model.document import Document

# BuildSuite project_status -> native ERPNext Project status (Open/Completed/Cancelled).
# New/Ongoing/Delayed all map to the active "Open"; only Completed closes the project.
_PROJECT_STATUS_TO_NATIVE = {
	"New": "Open",
	"Ongoing": "Open",
	"Delayed": "Open",
	"Completed": "Completed",
}


def sync_project_status(doc, method=None):
	"""Keep native `status` aligned with the BuildSuite `project_status` enum.

	project_status (New/Ongoing/Delayed/Completed) is the source of truth shown in
	the UI; the native status only carries Open/Completed/Cancelled, so we map onto
	it. Defaults a blank project_status to New.
	"""
	if not getattr(doc, "project_status", None):
		doc.project_status = "New"
	doc.status = _PROJECT_STATUS_TO_NATIVE.get(doc.project_status, "Open")

	# Progress is ALWAYS the weighted task rollup — fully decoupled from status.
	# erpnext's update_percent_complete (runs earlier in validate) otherwise (a) forces
	# percent to 100 when a project leaves the "Completed" status, and (b) re-derives
	# status from percent. Pin the method to Manual to silence its auto-calc, and on an
	# existing project recompute percent from our rollup here (after erpnext's pass) so
	# a status change never overwrites progress and 100% happens only when tasks do.
	doc.percent_complete_method = "Manual"
	if not doc.is_new():
		from buildsuite_core.utils.task import compute_project_progress

		doc.percent_complete = compute_project_progress(doc.name)


def set_company_on_insert(doc, method=None):
	"""Default/inherit company before insert (PRJ-005, PRJ-012).

	Subprojects inherit the parent's company; top-level projects fall back to the
	user's default company when none was chosen (covers single-company sites where
	the field is hidden in the UI).
	"""
	if doc.get("parent_project"):
		parent_company = frappe.db.get_value("Project", doc.parent_project, "company")
		if parent_company:
			doc.company = parent_company
			return

	if not doc.get("company"):
		# Inferred from the creating user's company (the Vue form no longer asks
		# for it), falling back to the site default.
		doc.company = (
			frappe.db.get_value("User", frappe.session.user, "company")
			or frappe.defaults.get_user_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)


def enforce_company_rules(doc, method=None):
	"""Lock company after create and keep subproject company inherited (PRJ-005, PRJ-013)."""
	# Subprojects always track their parent's company.
	if doc.get("parent_project"):
		parent_company = frappe.db.get_value("Project", doc.parent_project, "company")
		if parent_company:
			doc.company = parent_company

	# Company is read-only after create: revert any attempt to change it on edit.
	if not doc.is_new():
		before = doc.get_doc_before_save()
		if before and before.company and doc.company != before.company:
			doc.company = before.company


# Accounting / stock DocTypes that, if they reference a project, must block its
# deletion. Each entry: (doctype, fieldname holding the project link).
_FINANCIAL_LINKS = [
	("GL Entry", "project"),
	("Journal Entry Account", "project"),
	("Sales Invoice", "project"),
	("Purchase Invoice", "project"),
	("Stock Entry", "project"),
	("Payment Entry", "project"),
]


def _projects_in_tree(project):
	"""All project names in the subtree rooted at `project` (inclusive)."""
	names = [project]
	children = frappe.get_all("Project", filters={"parent_project": project}, pluck="name")
	for child in children:
		names.extend(_projects_in_tree(child))
	return names


def _assert_no_financial_links(project_names):
	for doctype, field in _FINANCIAL_LINKS:
		if not frappe.db.exists("DocType", doctype):
			continue
		# Only consider field if it exists on the doctype.
		meta = frappe.get_meta(doctype)
		if not meta.has_field(field):
			continue
		if frappe.db.exists(doctype, {field: ("in", project_names)}):
			frappe.throw(
				_(
					"Cannot delete: {0} records are linked to this project (or a subproject). "
					"Remove the accounting/stock entries first."
				).format(doctype)
			)


def cascade_delete_project(doc, method=None):
	"""Guarded cascade delete (PRJ-014, STG-011).

	Blocks if any accounting/stock entry references the project or its subprojects;
	otherwise removes subprojects, work packages, tasks, TPEs, stages, and
	attachments. Task deletion fires its own cascade (TPEs/attachments).
	"""
	project_names = _projects_in_tree(doc.name)
	_assert_no_financial_links(project_names)

	# Suppress progress rollup while we tear the tree down (tasks deleting here
	# would otherwise recompute ancestors that are about to be deleted too).
	previous = frappe.flags.get("buildsuite_cascading")
	frappe.flags.buildsuite_cascading = True
	try:
		# Delete descendants depth-first: child projects first (each re-enters this hook).
		for child in frappe.get_all("Project", filters={"parent_project": doc.name}, pluck="name"):
			frappe.delete_doc("Project", child, ignore_permissions=True, force=True)

		# Stage Plannings for this project.
		for stage in frappe.get_all("Stage Planning", filters={"project": doc.name}, pluck="name"):
			frappe.delete_doc("Stage Planning", stage, ignore_permissions=True, force=True)

		# Tasks (their on_trash cascades TPEs + attachments).
		for task in frappe.get_all("Task", filters={"project": doc.name}, pluck="name"):
			frappe.delete_doc("Task", task, ignore_permissions=True, force=True)

		# Work Packages.
		for wp in frappe.get_all("Work Package", filters={"project": doc.name}, pluck="name"):
			frappe.delete_doc("Work Package", wp, ignore_permissions=True, force=True)
	finally:
		frappe.flags.buildsuite_cascading = previous

	# Attachments on this project.
	_delete_attachments("Project", doc.name)


def _delete_attachments(doctype, name):
	for f in frappe.get_all(
		"File", filters={"attached_to_doctype": doctype, "attached_to_name": name}, pluck="name"
	):
		frappe.delete_doc("File", f, ignore_permissions=True, force=True)


def backfill_project_status(doc=None, method=None):
	"""Populate project_status on Projects where it's empty (idempotent).

	Derives from native status: Completed -> Completed, else New. Wired into
	after_migrate so existing projects render a badge.
	"""
	rows = frappe.get_all("Project", fields=["name", "status", "project_status"])
	updated = 0
	for row in rows:
		if row.project_status:
			continue
		new_status = "Completed" if row.status == "Completed" else "New"
		frappe.db.set_value("Project", row.name, "project_status", new_status, update_modified=False)
		updated += 1
	if updated:
		# Batch backfill run via `bench execute`/patch, which does not auto-commit;
		# the explicit commit persists the status updates.
		frappe.db.commit()  # nosemgrep
	return updated


def seed_from_template_on_insert(doc, method=None):
	"""Seed Work Packages, Tasks and Stages onto a new project from the ERPNext
	Project Template that matches its Project Category. Each layer is opt-in via the
	Project's seed flags; tasks link to the seeded Work Package by the template task's
	work-package code. Applies to sub-projects too — seeding is driven purely by the
	seed flags, so a sub-project that ticks them gets its category's template as well.
	"""
	category = doc.get("project_category")
	if not category:
		return

	seed_wps = bool(doc.get("custom_seed_default_work_packages"))
	seed_stages = bool(doc.get("custom_seed_default_stages"))
	seed_tasks = bool(doc.get("custom_seed_default_tasks"))
	if not (seed_wps or seed_stages or seed_tasks):
		return

	template_name = frappe.db.get_value("Project Template", {"project_category": category}, "name")
	if not template_name:
		return
	template = frappe.get_doc("Project Template", template_name)

	# --- Work Packages -----------------------------------------------------
	wp_by_code = {}
	if seed_wps:
		for row in sorted(template.custom_work_packages, key=lambda r: r.sort_order or 0):
			try:
				wp = frappe.get_doc(
					{
						"doctype": "Work Package",
						"project": doc.name,
						"code": row.code,
						"work_package_name": row.work_package_name,
						"budget": row.budget or 0,
						"description": row.description,
						"status": "Planned",
					}
				).insert(ignore_permissions=True)
				wp_by_code[row.code] = wp.name
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f'BuildSuite: seed work package "{row.code}" for project "{doc.name}"',
				)

	# --- Tasks (undated; scheduled later on the Gantt) — linked to their WP ---
	# Remember which seeded tasks belong to which template stage so the stages
	# below can pick them up into their stage_planning_tasks list.
	tasks_by_stage = {}
	if seed_tasks:
		for row in template.tasks:
			try:
				tt = frappe.get_doc("Task", row.task)  # the template Task
				task = frappe.get_doc(
					{
						"doctype": "Task",
						"project": doc.name,
						"subject": tt.subject,
						"priority": tt.priority or "Medium",
						"expected_time": tt.expected_time or 0,
						"work_package": wp_by_code.get(row.get("custom_work_package_code")),
						"task_status": "Yet To Start",
					}
				).insert(ignore_permissions=True)
				stage = row.get("custom_stage")
				if stage:
					tasks_by_stage.setdefault(stage, []).append(task.name)
			except Exception:
				frappe.log_error(
					frappe.get_traceback(),
					f'BuildSuite: seed task "{row.task}" for project "{doc.name}"',
				)

	# --- Stages (planned dates from the template offsets, clamped to bounds) ---
	if seed_stages:
		try:
			_seed_stages_from_template(doc, template, tasks_by_stage)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(), f'BuildSuite: seed stages for project "{doc.name}"'
			)


@frappe.whitelist()
def get_project_template_summary(project_category: str = None, project_type: str = None):
	"""Preview of the template for a Project Category (used by the create form):
	its stage names, work-package count and task count. `project_type` is accepted
	for backward compatibility with older callers."""
	category = project_category or project_type
	if not category:
		return {"exists": False}

	template_name = frappe.db.get_value("Project Template", {"project_category": category}, "name")
	if not template_name:
		return {"exists": False}

	template = frappe.get_doc("Project Template", template_name)
	stage_names = [s.stage_name for s in (template.custom_stages or [])]
	return {
		"exists": True,
		"stage_names": stage_names,
		"stage_count": len(stage_names),
		"work_package_count": len(template.custom_work_packages or []),
		"task_count": len(template.tasks or []),
	}


def _seed_stages_from_template(project_doc, template, tasks_by_stage=None):
	"""Append the template's stages onto a project, dates clamped to the project's
	own window so date-bounds validation passes. When tasks_by_stage maps a stage
	name to seeded Task names, those tasks are added to the stage's task list (at a
	default planned qty of 100%). Returns the count of stages created."""
	from frappe.utils import add_days, getdate, today

	tasks_by_stage = tasks_by_stage or {}
	base = project_doc.expected_start_date or today()
	end_bound = project_doc.expected_end_date

	def _clamp(d):
		if end_bound and getdate(d) > getdate(end_bound):
			return end_bound
		return d

	count = 0
	for row in template.custom_stages:
		stage = frappe.get_doc(
			{
				"doctype": "Stage Planning",
				"project": project_doc.name,
				"stage_name": row.stage_name,
				"planned_start": _clamp(add_days(base, row.offset_start_days or 0)),
				"planned_end": _clamp(add_days(base, row.offset_end_days or 0)),
				"planned_task_count": row.planned_task_count or 0,
				"planned_completion_pct": row.planned_completion_pct or 0,
				"workflow_state": "Draft",
			}
		)
		for task_name in tasks_by_stage.get(row.stage_name, []):
			stage.append("stage_planning_tasks", {"task": task_name, "planned_qty": 100, "qty_unit": "%"})
		stage.insert(ignore_permissions=True)
		count += 1
	return count


@frappe.whitelist()
def seed_stages_from_template(project: str):
	"""Append the matching category template's stages onto an EXISTING project.
	Mirrors the create-time seed. Returns the number of stages created."""
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")

	category = doc.get("project_category")
	if not category:
		frappe.throw(_("This project has no Project Category, so there is no template to seed from."))

	template_name = frappe.db.get_value("Project Template", {"project_category": category}, "name")
	if not template_name:
		frappe.throw(_("No template is configured for category {0}.").format(category))

	template = frappe.get_doc("Project Template", template_name)

	# Attach the project's existing tasks to the stage they belong to in the
	# template (matched by subject), so re-seeded stages arrive with their tasks
	# just like the create-time import does.
	stage_by_subject = {}
	for row in template.tasks:
		subject = frappe.db.get_value("Task", row.task, "subject")
		if subject and row.get("custom_stage"):
			stage_by_subject[subject] = row.custom_stage
	tasks_by_stage = {}
	for t in frappe.get_all("Task", filters={"project": doc.name}, fields=["name", "subject"]):
		stage = stage_by_subject.get(t.subject)
		if stage:
			tasks_by_stage.setdefault(stage, []).append(t.name)

	return {"seeded": _seed_stages_from_template(doc, template, tasks_by_stage)}


def ensure_project_team_membership(doc, method=None):
	"""PRM-002 — project visibility is team-membership based. Ensure the project's
	creator and its assigned project_manager are team members, so the project is
	visible to them under the team-scoped permission model. Idempotent; inserts the
	child rows directly to avoid re-triggering the parent's on_update.
	"""
	_ensure_team_member(doc.name, doc.owner)
	_ensure_team_member(doc.name, getattr(doc, "project_manager", None))


def _ensure_team_member(project_name, user):
	if not user or user == "Administrator":
		return
	if not frappe.db.exists("User", user):
		return
	if frappe.db.exists(
		"Project Team",
		{
			"parenttype": "Project",
			"parentfield": "custom_team_members",
			"parent": project_name,
			"user": user,
		},
	):
		return
	frappe.get_doc(
		{
			"doctype": "Project Team",
			"parenttype": "Project",
			"parentfield": "custom_team_members",
			"parent": project_name,
			"user": user,
			"full_name": frappe.db.get_value("User", user, "full_name"),
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def create_warehouse_for_project(doc: Document, method: str | None = None):
	# Create Projects Group Warehouse
	if not frappe.db.exists("Warehouse", {"warehouse_name": "Projects", "company": doc.company}):
		warehouse = frappe.new_doc("Warehouse")
		warehouse.warehouse_name = "Projects"
		warehouse.company = doc.company
		warehouse.is_group = 1
		warehouse.insert(ignore_permissions=True)

	parent_warehouse = frappe.db.get_value(
		"Warehouse", {"warehouse_name": "Projects", "company": doc.company}, "name"
	)

	# Create Project Group Warehouse
	if not frappe.db.exists("Warehouse", {"warehouse_name": doc.project_name, "company": doc.company}):
		warehouse = frappe.new_doc("Warehouse")
		warehouse.warehouse_name = doc.project_name
		warehouse.parent_warehouse = parent_warehouse
		warehouse.company = doc.company
		warehouse.is_group = 1
		warehouse.insert(ignore_permissions=True)

	project_parent_warehouse = frappe.db.get_value(
		"Warehouse", {"warehouse_name": doc.project_name, "company": doc.company}, "name"
	)

	# Create Store Warehouse
	project_warehouse = f"{doc.project_name} Store"

	if not frappe.db.exists("Warehouse", {"warehouse_name": project_warehouse, "company": doc.company}):
		stock_account = frappe.db.get_value(
			"Account", {"account_type": "Stock", "company": doc.company, "is_group": 0}, "name"
		)

		warehouse = frappe.new_doc("Warehouse")
		warehouse.warehouse_name = project_warehouse
		warehouse.project = doc.name
		warehouse.parent_warehouse = project_parent_warehouse
		warehouse.account = stock_account
		warehouse.company = doc.company
		warehouse.insert(ignore_permissions=True)


@frappe.whitelist()
def delete_warehouse_for_project(doc: Document, method: str | None = None):
	"""Remove the per-project warehouses created in create_warehouse_for_project so a
	project delete leaves no orphans: the "<project> Store" leaf first, then its
	"<project>" group parent once empty. The shared company-level "Projects" group is
	left intact — other projects hang off it."""
	store = frappe.db.get_value(
		"Warehouse", {"warehouse_name": f"{doc.project_name} Store", "company": doc.company}, "name"
	)
	if store:
		frappe.delete_doc("Warehouse", store, ignore_permissions=True, force=True)

	# The per-project group warehouse (parent of the Store) was previously left
	# orphaned. Remove it too, but only once it has no remaining child warehouses.
	group = frappe.db.get_value(
		"Warehouse",
		{"warehouse_name": doc.project_name, "company": doc.company, "is_group": 1},
		"name",
	)
	if group and not frappe.db.count("Warehouse", {"parent_warehouse": group}):
		frappe.delete_doc("Warehouse", group, ignore_permissions=True, force=True)
