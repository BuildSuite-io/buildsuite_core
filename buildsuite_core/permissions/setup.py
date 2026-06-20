"""Seed BuildSuite roles and Project/Task DocPerms.

Run idempotently from install.after_migrate / after_install. The CRUD matrices
here are the single source of truth for the per-persona base permissions; the
team-membership scoping (and Task own-scope rules) are layered on top in
buildsuite_core.permissions.project and buildsuite_core.permissions.task.
"""

import frappe

# Per-role base permissions on Project at permlevel 0 (from the persona spec).
# System Manager is intentionally absent — it keeps its native full Project perms.
PROJECT_ROLE_PERMS = {
	"BuildSuite Director": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite PM": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Administrator": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite Estimator": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite QS": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Procurement Officer": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Accountant": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite HR Manager": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Site Engineer": {"read": 1, "report": 1, "print": 1},
	"BuildSuite Store Keeper": {"read": 1, "report": 1, "print": 1},
	"BuildSuite Foreman": {"read": 1, "print": 1},
}

# Per-role base permissions on Task at permlevel 0 (from the Task persona spec).
# Site Engineer / Foreman get write+create+delete at the DocPerm level; the
# own-scope restriction (edit/delete only own-created or assigned tasks) is
# enforced in buildsuite_core.permissions.task.has_task_permission, since a
# has_permission hook can only DENY, never widen, a DocPerm grant.
TASK_ROLE_PERMS = {
	"BuildSuite Director": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite PM": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Administrator": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite Estimator": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite QS": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Site Engineer": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "print": 1},
	"BuildSuite Foreman": {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1},
	"BuildSuite Procurement Officer": {"read": 1, "report": 1, "print": 1},
	"BuildSuite Store Keeper": {"read": 1, "report": 1, "print": 1},
	"BuildSuite Accountant": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite HR Manager": {"read": 1, "report": 1, "print": 1},
}

# Per-role base permissions on Work Package — read-only for everyone except the
# full-CRUD roles; scope inherits the parent project. No own-scope rules.
WORK_PACKAGE_ROLE_PERMS = {
	"BuildSuite Director": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite PM": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Administrator": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite Estimator": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite QS": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Site Engineer": {"read": 1, "report": 1, "print": 1},
	"BuildSuite Foreman": {"read": 1, "print": 1},
	"BuildSuite Procurement Officer": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Store Keeper": {"read": 1, "report": 1, "print": 1},
	"BuildSuite Accountant": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite HR Manager": {"read": 1, "report": 1, "print": 1},
}

# Per-role base permissions on Task Progress Entry. Procurement Officer and Store
# Keeper are HIDDEN (no DocPerm at all). Site Engineer / Foreman get write+create
# +delete here; the own-scope (edit own; delete own within 24h) is enforced in
# buildsuite_core.permissions.task_progress_entry. HR's labour-fields-only field
# restriction is deferred (read-all at permlevel 0 for now).
TASK_PROGRESS_ENTRY_ROLE_PERMS = {
	"BuildSuite Director": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite PM": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Administrator": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite Estimator": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite QS": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Site Engineer": {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1},
	"BuildSuite Foreman": {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1},
	"BuildSuite Accountant": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite HR Manager": {"read": 1, "report": 1, "export": 1},  # print withheld per spec
}

# Per-role base permissions on Stage Planning (permlevel 0). Procurement / Store
# Keeper hidden. Site Engineer / Foreman get write+create+delete with own-scope
# (created-by, Draft/Rejected only) enforced in code. The Submit/Approve/Reject/
# Revise workflow actions live on the Stage Planning Approval workflow, rewired by
# setup_stage_planning_workflow(). Print is granted to every readable role.
STAGE_PLANNING_ROLE_PERMS = {
	"BuildSuite Director": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite PM": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Administrator": {
		"read": 1,
		"write": 1,
		"create": 1,
		"delete": 1,
		"report": 1,
		"export": 1,
		"print": 1,
	},
	"BuildSuite Estimator": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite QS": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite Site Engineer": {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "print": 1},
	"BuildSuite Foreman": {"read": 1, "write": 1, "create": 1, "delete": 1, "print": 1},
	"BuildSuite Accountant": {"read": 1, "report": 1, "export": 1, "print": 1},
	"BuildSuite HR Manager": {"read": 1, "report": 1, "print": 1},
}

# Reference doctypes the BuildSuite Project / Task / Stage surfaces link to. Any
# role that can READ Project must be able to read these, or the list filters /
# link pickers / template previews 403 (and the SPA surfaces it as an unhandled
# rejection). The rule: "if you can read a Project, you can read what a Project
# links to." We mirror ONLY the role's non-destructive Project permissions
# (read/report/export/print) — BuildSuite never grants write/create/delete on
# these masters, whether they're ERPNext/HR-owned (Company, Customer, Project
# Type, Employee, Task Type) or our own reference data (BuildSuite Project
# Template, read-only for the create-from-template preview/seed).
LINKED_MASTER_DOCTYPES = (
	"Company",  # Projects list multi-company filter
	"Customer",  # New Project -> Client picker
	"Project Type",  # New Project -> Project Type picker
	"Employee",  # PM / owner / assignee pickers
	"Task Type",  # New Task -> Task Type picker
	"BuildSuite Project Template",  # New Project -> template preview + seed
)
_READONLY_PTYPES = ("read", "report", "export", "print")

# No-DocPerm marker role granted to every persona. Used ONLY as the Stage Planning
# workflow states' `allow_edit` (a mandatory single-role field) so the workflow
# never blocks editing — the real edit gate is DocPerm + has_*_permission.
WORKFLOW_EDITOR_ROLE = "BuildSuite Project User"

# All BuildSuite roles, for the app-level access gate (api.permission).
BUILDSUITE_ROLES = tuple(PROJECT_ROLE_PERMS.keys())

# User.persona Select value -> the role that persona grants. The persona option
# strings mirror the `name` fields in frontend/src/data/roles.js so the frontend
# and backend agree on one vocabulary. "System Manager (Admin)" maps to Frappe's
# native System Manager role (not a BuildSuite role).
PERSONA_TO_ROLE = {
	"Director / Owner": "BuildSuite Director",
	"Project Manager": "BuildSuite PM",
	"Estimator": "BuildSuite Estimator",
	"Quantity Surveyor": "BuildSuite QS",
	"Site Engineer": "BuildSuite Site Engineer",
	"Foreman / Supervisor": "BuildSuite Foreman",
	"Procurement Officer": "BuildSuite Procurement Officer",
	"Store Keeper": "BuildSuite Store Keeper",
	"Accountant": "BuildSuite Accountant",
	"HR Manager": "BuildSuite HR Manager",
	"System Manager (Admin)": "System Manager",
	"BuildSuite Administrator": "BuildSuite Administrator",
}

# Every flag we may set on a DocPerm — anything not granted is explicitly cleared.
_PTYPES = ("read", "write", "create", "delete", "report", "export", "print")


def _ensure_role(role_name):
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)


def _apply_role_perms(doctype, role_perms):
	from frappe.permissions import add_permission, update_permission_property

	for role, perms in role_perms.items():
		_ensure_role(role)
		add_permission(doctype, role, 0)
		for ptype in _PTYPES:
			update_permission_property(
				doctype,
				role,
				0,
				ptype,
				perms.get(ptype, 0),
				validate=False,
			)


def setup_project_permissions():
	_apply_role_perms("Project", PROJECT_ROLE_PERMS)


def setup_task_permissions():
	_apply_role_perms("Task", TASK_ROLE_PERMS)


def setup_work_package_permissions():
	_apply_role_perms("Work Package", WORK_PACKAGE_ROLE_PERMS)


def setup_task_progress_entry_permissions():
	_apply_role_perms("Task Progress Entry", TASK_PROGRESS_ENTRY_ROLE_PERMS)


def setup_stage_planning_permissions():
	_apply_role_perms("Stage Planning", STAGE_PLANNING_ROLE_PERMS)


def _readonly_mirror(role_perms):
	"""Reduce a role-perm matrix to its non-destructive ptypes, for read roles.

	Used to derive Company/Customer perms from PROJECT_ROLE_PERMS: a role keeps
	only its read/report/export/print grants (write/create/delete are dropped),
	and roles without read on Project are excluded entirely.
	"""
	return {
		role: {ptype: perms.get(ptype, 0) for ptype in _READONLY_PTYPES}
		for role, perms in role_perms.items()
		if perms.get("read")
	}


def setup_linked_master_permissions():
	"""Grant read-only Company/Customer access to every Project-readable role.

	The Projects list filters on Company and the New Project form links Client to
	Customer; without read on these masters those calls 403. Mirrors only the
	non-destructive Project permissions (see LINKED_MASTER_DOCTYPES note).
	"""
	mirror = _readonly_mirror(PROJECT_ROLE_PERMS)
	for doctype in LINKED_MASTER_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			_apply_role_perms(doctype, mirror)


# Stage Planning Approval transitions, keyed to BuildSuite roles.
# (state, action, next_state, [roles], own_only)
_STAGE_FULL_ROLES = ["BuildSuite Director", "BuildSuite PM", "BuildSuite Administrator", "System Manager"]
_STAGE_TRANSITIONS = [
	("Draft", "Submit for Approval", "Pending Approval", _STAGE_FULL_ROLES, False),
	(
		"Draft",
		"Submit for Approval",
		"Pending Approval",
		["BuildSuite Site Engineer", "BuildSuite Foreman"],
		True,
	),
	("Pending Approval", "Approve", "Approved", _STAGE_FULL_ROLES, False),
	("Pending Approval", "Reject", "Rejected", _STAGE_FULL_ROLES, False),
	# Rejected is terminal — no Revise after a rejection (a new stage must be created).
	("Approved", "Revise", "Draft", _STAGE_FULL_ROLES, False),
	("Approved", "Cancel", "Cancelled", _STAGE_FULL_ROLES, False),
]


def setup_stage_planning_workflow():
	"""Rewire the Stage Planning Approval workflow to BuildSuite roles.

	States' allow_edit is set to the permissive marker role so the workflow never
	blocks editing (DocPerm + has_stage_planning_permission is the real gate).
	Transitions are rebuilt per the persona matrix; Site Engineer / Foreman can
	only submit their OWN draft stages (workflow condition on doc.owner).
	"""
	if not frappe.db.exists("Workflow", "Stage Planning Approval"):
		return

	wf = frappe.get_doc("Workflow", "Stage Planning Approval")
	for state in wf.states:
		state.allow_edit = WORKFLOW_EDITOR_ROLE

	wf.set("transitions", [])
	for state, action, next_state, roles, own_only in _STAGE_TRANSITIONS:
		condition = "doc.owner == frappe.session.user" if own_only else ""
		for role in roles:
			wf.append(
				"transitions",
				{
					"state": state,
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"condition": condition,
					"allow_self_approval": 1,
				},
			)
	wf.save(ignore_permissions=True)


def setup_record_permissions():
	"""Seed roles + DocPerms for every BuildSuite-scoped doctype."""
	setup_project_permissions()
	setup_task_permissions()
	setup_work_package_permissions()
	setup_task_progress_entry_permissions()
	setup_stage_planning_permissions()
	setup_linked_master_permissions()
	_ensure_role(WORKFLOW_EDITOR_ROLE)
	setup_stage_planning_workflow()
