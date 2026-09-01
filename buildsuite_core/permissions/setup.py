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

# The estimation write roles: BuildSuite Administrator + Director + PM + Estimator +
# QS. System Manager is omitted here — it keeps native full perms on custom doctypes.
_ESTIMATION_ROLES = (
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Estimator",
	"BuildSuite QS",
)

# BOQ (Bill of Quantities) — full CRUD for the estimation roles; everyone else has
# NO access (the Estimation workspace is hidden from them). M2 tightened this from
# the earlier "read for Site Engineer / Foreman / Accountant / HR".
_BOQ_FULL = {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1}
_BOQ_READ = {"read": 1, "report": 1, "export": 1, "print": 1}
BOQ_ROLE_PERMS = {role: _BOQ_FULL for role in _ESTIMATION_ROLES}
BOQ_DOCTYPES = ("BOQ", "BOQ Group", "BOQ Item", "BOQ Sub Item")

# Only these roles may approve a BOQ (mirrors the prototype BOQ_APPROVE_ROLES). The
# approve_boq API enforces this server-side.
BOQ_APPROVE_ROLES = (
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Administrator",
	"System Manager",
)

# Masters the BOQ tree's link pickers resolve. Any BOQ-readable role needs read on
# these or the pickers 403 (read-only mirror — never write).
BOQ_LINKED_MASTER_DOCTYPES = ("UOM", "Construction Rate Master", "Assembly", "Estimate Template")

# --- M2 estimation masters + Purchase & Stock matrices ----------------------
# Permission-code shorthands (readme: C R W D S X — Create/Read/Write/Delete/Submit/
# Cancel-Amend). CRWDSX = full on a submittable doctype; CRWD = full non-submittable.
_READ = {"read": 1, "report": 1, "export": 1, "print": 1}  # R
_FULL = {"read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "export": 1, "print": 1}  # CRWD
_FULL_SUB = {**_FULL, "submit": 1, "cancel": 1, "amend": 1}  # CRWDSX
_RAISE = {"read": 1, "create": 1, "print": 1}  # CR — raise own records only
_CRWS = {"read": 1, "write": 1, "create": 1, "submit": 1, "report": 1, "print": 1}  # CRWS
_CRW = {"read": 1, "write": 1, "create": 1, "report": 1, "print": 1}  # CRW — edit, no delete
# Select-only: the role may resolve the doctype in a LINK-FIELD PICKER (frappe.get_list honours
# `select` — verified) but cannot list / report / export it. Used for reference masters a persona
# only ever picks, never opens a screen for. Applied with _SELECT_PTYPES so read is cleared.
_SELECT = {"select": 1, "print": 1}  # S — pick in a link field, no read

# Assembly + Estimate Template: full for the estimation roles, hidden for the rest.
ASSEMBLY_TEMPLATE_ROLE_PERMS = {role: _FULL for role in _ESTIMATION_ROLES}
# Rate Master: full for the estimation roles; Procurement Officer is READ-ONLY here
# (the ruling) — it writes to the catalog only via the gated PO-submit dialog, never
# this form. Rate History is the parent's child table, so its read follows Rate Master.
RATE_MASTER_ROLE_PERMS = {
	**{role: _FULL for role in _ESTIMATION_ROLES},
	"BuildSuite Procurement Officer": _READ,
}
# UOM is resolved by the BOQ / Rate Master link pickers, so those roles need read.
_UOM_READ_ROLES = _ESTIMATION_ROLES + ("BuildSuite Procurement Officer",)

# Purchase & Stock (native ERPNext doctypes). `project` is required per config and
# drives warehouse defaulting; the rate-update prompt on PO submit is gated
# separately (RATE_UPDATE_GOVERNANCE_ROLES).
MATERIAL_REQUEST_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _CRWS,  # PM authors + submits; approval is the workflow action
	"BuildSuite Site Engineer": _RAISE,  # raise own MR only
	"BuildSuite Foreman": _RAISE,  # raise own MR only
	"BuildSuite Procurement Officer": _FULL_SUB,
	"BuildSuite Store Keeper": _READ,
	"BuildSuite Accountant": _READ,
}
PURCHASE_ORDER_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _READ,
	"BuildSuite Procurement Officer": _FULL_SUB,
	"BuildSuite Store Keeper": _READ,
	"BuildSuite Accountant": _READ,
}
PURCHASE_RECEIPT_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _READ,
	"BuildSuite Procurement Officer": _FULL_SUB,
	"BuildSuite Store Keeper": _FULL_SUB,  # Store Keeper posts receipts
	"BuildSuite Accountant": _READ,
}
PURCHASE_INVOICE_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	# Supplier Bill — the Director/Owner owns supplier invoicing end to end, so full CRWDSX
	# (not read-only): raise, edit, submit, cancel + amend a supplier invoice.
	"BuildSuite Director": _FULL_SUB,
	"BuildSuite PM": _CRW,  # PM raises + edits supplier bills; the Accountant submits/cancels them
	"BuildSuite Procurement Officer": _READ,
	"BuildSuite Store Keeper": _READ,  # reads supplier bills (custody/receipt context), never edits
	"BuildSuite Accountant": _FULL_SUB,  # Accountant owns invoicing
}
STOCK_ENTRY_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _READ,
	"BuildSuite Site Engineer": _CRWS,  # posts Material Issue for consumption
	"BuildSuite Procurement Officer": _FULL_SUB,
	"BuildSuite Store Keeper": _FULL_SUB,
	"BuildSuite Accountant": _READ,
}
ITEM_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _READ,
	"BuildSuite Estimator": _READ,
	"BuildSuite QS": _READ,
	"BuildSuite Procurement Officer": _FULL,  # maintains Item.rate_master
	"BuildSuite Store Keeper": _FULL,
	"BuildSuite Accountant": _READ,
}

# Roles that may confirm a Rate Master rate update from the PO-submit dialog. The
# Procurement Officer is empowered-with-guardrails here even though it is READ-ONLY
# on the Rate Master form. Enforced server-side in buildsuite_core.api.rate_master.
RATE_UPDATE_GOVERNANCE_ROLES = (
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Estimator",
	"BuildSuite QS",
	"BuildSuite Procurement Officer",
	"BuildSuite Administrator",
	"System Manager",
	"Administrator",
)

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
	"Project Type",  # native Internal / External
	"Project Category",  # New Project -> Category picker (drives templating)
	"Employee",  # PM / owner / assignee pickers
	"Task Type",  # New Task -> Task Type picker
	"Persona",  # Users settings -> persona link picker
)
_READONLY_PTYPES = ("read", "report", "export", "print")

# No-DocPerm marker role granted to every persona. Used ONLY as the Stage Planning
# workflow states' `allow_edit` (a mandatory single-role field) so the workflow
# never blocks editing — the real edit gate is DocPerm + has_*_permission.
WORKFLOW_EDITOR_ROLE = "BuildSuite Project User"

# All BuildSuite roles, for the app-level access gate (api.permission).
BUILDSUITE_ROLES = tuple(PROJECT_ROLE_PERMS.keys())

# The persona -> role mapping now lives in the Persona master (seeded from
# buildsuite_core.buildsuite_core.doctype.persona.seed_personas). utils.user reads
# a user's Persona.roles to keep their BuildSuite roles in sync.

# Every flag we may set on a DocPerm — anything not granted is explicitly cleared.
_PTYPES = ("read", "write", "create", "delete", "report", "export", "print")
# Submittable doctypes (Material Request, Purchase Order, Stock Entry, …) also carry
# the transition ptypes.
_SUBMIT_PTYPES = _PTYPES + ("submit", "cancel", "amend")
# Picker-only reference masters carry `select` too — include it so a _SELECT grant sets select=1
# AND clears read/report/export/print (which are in _PTYPES).
_SELECT_PTYPES = _PTYPES + ("select",)


def _ensure_role(role_name):
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)


def _grant_system_manager(doctype):
	"""Re-grant System Manager full access on `doctype`.

	System Manager is Frappe's native super-admin, but a doctype's *Custom* DocPerms COMPLETELY
	override its standard perms — so the moment we add any BuildSuite Custom DocPerm, SM loses
	its native grant unless we re-add it here. Give SM the full set (CRWD, plus submit/cancel/
	amend on submittable doctypes), matching the M-series matrices where SM is full everywhere.
	Idempotent — safe to call from every _apply/_upgrade pass over the same doctype."""
	from frappe.permissions import add_permission, update_permission_property

	ptypes = _SUBMIT_PTYPES if frappe.db.get_value("DocType", doctype, "is_submittable") else _PTYPES
	add_permission(doctype, "System Manager", 0)
	for ptype in ptypes:
		update_permission_property(doctype, "System Manager", 0, ptype, 1, validate=False)


def _apply_role_perms(doctype, role_perms, ptypes=_PTYPES):
	if not frappe.db.exists("DocType", doctype):
		return
	from frappe.permissions import add_permission, update_permission_property

	# The matrix is the single source of truth: drop any stale custom grant for a
	# BuildSuite role no longer listed (e.g. a role dropped from an earlier read
	# mirror), so removing a role from a matrix actually revokes its access.
	for role in set(BUILDSUITE_ROLES) - set(role_perms):
		frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role})

	_grant_system_manager(doctype)

	for role, perms in role_perms.items():
		_ensure_role(role)
		add_permission(doctype, role, 0)
		for ptype in ptypes:
			update_permission_property(
				doctype,
				role,
				0,
				ptype,
				perms.get(ptype, 0),
				validate=False,
			)


def _upgrade_role_perms(doctype, role_perms, ptypes=_PTYPES):
	"""Raise perms for specific roles WITHOUT revoking anyone else — layer write/delete on top
	of a read mirror. Customer and Employee are readable by many roles (link pickers), but only
	some may write/delete them; _apply_role_perms would revoke every unlisted role's read, so
	use this to upgrade the writers while the mirror keeps the readers."""
	if not frappe.db.exists("DocType", doctype):
		return
	from frappe.permissions import add_permission, update_permission_property

	_grant_system_manager(doctype)
	for role, perms in role_perms.items():
		_ensure_role(role)
		add_permission(doctype, role, 0)
		for ptype in ptypes:
			update_permission_property(doctype, role, 0, ptype, perms.get(ptype, 0), validate=False)


def setup_project_permissions():
	_apply_role_perms("Project", PROJECT_ROLE_PERMS)


def setup_task_permissions():
	_apply_role_perms("Task", TASK_ROLE_PERMS)


def setup_schedule_snapshot_permissions():
	# Schedule undo/revision snapshots follow Task-edit rights — whoever can change
	# the schedule can capture, restore and delete its snapshots. Restore additionally
	# enforces per-Task write on save.
	_apply_role_perms("Schedule Snapshot", TASK_ROLE_PERMS)


def setup_work_package_permissions():
	_apply_role_perms("Work Package", WORK_PACKAGE_ROLE_PERMS)


def setup_task_progress_entry_permissions():
	_apply_role_perms("Task Progress Entry", TASK_PROGRESS_ENTRY_ROLE_PERMS)


def setup_stage_planning_permissions():
	_apply_role_perms("Stage Planning", STAGE_PLANNING_ROLE_PERMS)


def setup_boq_permissions():
	for doctype in BOQ_DOCTYPES:
		_apply_role_perms(doctype, BOQ_ROLE_PERMS)


def setup_estimation_master_permissions():
	"""Assembly / Estimate Template / Rate Master (+ UOM read for their link pickers).
	Rate Master's Rate History is a child table, so its read follows the parent."""
	for doctype in ("Assembly", "Estimate Template"):
		_apply_role_perms(doctype, ASSEMBLY_TEMPLATE_ROLE_PERMS)
	_apply_role_perms("Construction Rate Master", RATE_MASTER_ROLE_PERMS)
	# UOM is a pure link-picker target (unit dropdown on BOQ / Rate Master) — select, not read.
	_apply_role_perms("UOM", {role: _SELECT for role in _UOM_READ_ROLES}, _SELECT_PTYPES)


def setup_purchase_stock_permissions():
	"""BuildSuite-role DocPerms on the native ERPNext buying / stock doctypes."""
	_apply_role_perms("Material Request", MATERIAL_REQUEST_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Purchase Order", PURCHASE_ORDER_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Purchase Receipt", PURCHASE_RECEIPT_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Purchase Invoice", PURCHASE_INVOICE_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Stock Entry", STOCK_ENTRY_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Item", ITEM_ROLE_PERMS)


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


# --- Subcontract module -------------------------------------------------------
_SUBCONTRACT_FULL_ROLES = (
	"BuildSuite Procurement Officer",
	"BuildSuite PM",
	"BuildSuite Director",
	"BuildSuite Administrator",
)
_SUBCONTRACT_READ_ROLES = ("BuildSuite QS", "BuildSuite Site Engineer", "BuildSuite Accountant")
SUBCONTRACT_ROLE_PERMS = {
	**{role: _FULL for role in _SUBCONTRACT_FULL_ROLES},
	**{role: _READ for role in _SUBCONTRACT_READ_ROLES},
	"BuildSuite PM": _CRW,  # PM maintains subcontractors (edit) but does not delete them
	"BuildSuite QS": _FULL,  # QS maintains subcontractors fully (per the QS ruling), not read-only
	"BuildSuite Accountant": _FULL,  # Accountant maintains subcontractors fully (per the Accountant ruling)
	"BuildSuite Estimator": _READ,  # Estimator reads subcontractors (per the Estimator ruling)
}
# Trade / Delivery Type masters — pure WO link-picker targets (no screen), so everyone in the
# module only SELECTs them; Procurement + admins maintain the master (full CRWD).
SUBCONTRACT_MASTER_ROLE_PERMS = {
	**{role: _SELECT for role in _SUBCONTRACT_FULL_ROLES + _SUBCONTRACT_READ_ROLES},
	"BuildSuite Procurement Officer": _FULL,
	"BuildSuite Administrator": _FULL,
}
# Measurement Book — the QS records + certifies site measurements (full CRUD). The
# Site Engineer only RAISES measurement books (create + read; no edit/delete/certify,
# per the Site Engineer ruling), so it's create-only below, not full. The Director is
# oversight-only (read, per the Director/Owner ruling). The Procurement Officer has NO
# MB access at all (per the Procurement ruling), so it is excluded from the full roles
# and gets no grant (revoked by _apply_role_perms).
_MB_FULL_ROLES = tuple(r for r in _SUBCONTRACT_FULL_ROLES if r != "BuildSuite Procurement Officer") + (
	"BuildSuite QS",
)
MEASUREMENT_BOOK_ROLE_PERMS = {
	**{role: _FULL for role in _MB_FULL_ROLES},
	"BuildSuite Site Engineer": _RAISE,  # raise only — create + read, never edit/delete/certify
	"BuildSuite Director": _READ,  # oversight only — read, never edit
	"BuildSuite Estimator": _READ,  # read-only (per the Estimator ruling)
	"BuildSuite Accountant": _READ,
}
# Subcontractor Bill (RA Bill) — submittable. The QS + subcontract full roles raise and
# submit progress bills; the Accountant + Site Engineer + Estimator read them. Every role that
# can read a Work Order reads Bills too — the WO list shows a "% billed" column sourced from
# them, so a WO reader without Bill read would 403 the whole list.
# NOTE: `_BILL_FULL_ROLES` is shared with the Work Order matrix (where the Director stays
# full CRWDSX). On the Bill, the Director is oversight-only — the explicit `_READ` below wins
# over the `_FULL_SUB` spread, so the Director reads bills but never raises/submits them.
_BILL_FULL_ROLES = _SUBCONTRACT_FULL_ROLES + ("BuildSuite QS",)
SUBCONTRACT_BILL_ROLE_PERMS = {
	**{role: _FULL_SUB for role in _BILL_FULL_ROLES},
	"BuildSuite Director": _READ,  # oversight only — read, never raise/submit a bill
	"BuildSuite PM": _CRW,  # PM prepares bills (create/edit) but the QS submits them
	"BuildSuite Procurement Officer": _CRW,  # prepares bills (create/edit); QS submits, so no S/X
	"BuildSuite Accountant": _FULL_SUB,  # Accountant owns bill posting fully (per the Accountant ruling)
	"BuildSuite Site Engineer": _READ,
	# Estimator has NO Subcontractor Bill access (per the Estimator ruling) — omitted, so
	# _apply_role_perms revokes any prior grant.
}
# Subcontractor Work Order — the commitment document is natively submittable (Draft →
# Submitted → Cancelled + Amend), so the full roles get CRWDSX, not just CRWD. QS prepares
# and submits alongside PM / Procurement / Director; Estimator / Site Engineer / Accountant
# read. (Matches the M3 matrix; the old grant gave CRWD only, so no one could submit/cancel.)
SUBCONTRACT_WO_ROLE_PERMS = {
	**{role: _FULL_SUB for role in _BILL_FULL_ROLES},
	"BuildSuite Estimator": _READ,
	"BuildSuite Site Engineer": _READ,
	"BuildSuite Accountant": _READ,
}

# Scope Change Order — role matrix (SCO is header-only + status-based, not submittable,
# so Submit/Cancel don't apply; "full" = CRWD). PM/QS prepare + quantify, Director
# approves; approval is gated in api/sco.py to BOQ_APPROVE_ROLES (PM / Director / Admin).
# The Site Engineer can *raise* (create) and read only their OWN change orders
# (own-scope enforced in permissions/sco.py); Foreman / Store Keeper / HR Manager have
# no access; Estimator / Procurement Officer / Accountant are read-only.
SCO_ROLE_PERMS = {
	"BuildSuite Director": _FULL,
	"BuildSuite PM": _FULL,
	"BuildSuite QS": _FULL,
	"BuildSuite Administrator": _FULL,
	"BuildSuite Estimator": _READ,
	"BuildSuite Site Engineer": _RAISE,  # create-own; cannot approve
	"BuildSuite Procurement Officer": _READ,
	"BuildSuite Accountant": _READ,
}


def setup_sco_permissions():
	_apply_role_perms("Scope Change Order", SCO_ROLE_PERMS)


# --- Project Finance — Petty Cash -------------------------------------------
# Site roles (Site Engineer / Foreman) raise + manage their own requests; finance
# roles have full access. Disbursing is gated in the API by PETTY_CASH_DISBURSE_ROLES,
# not a DocPerm (any writer can save a request; only approvers can disburse).
_PETTY_CASH_SITE = {"read": 1, "write": 1, "create": 1, "report": 1, "print": 1}
PETTY_CASH_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite Director": _FULL,
	"BuildSuite PM": _FULL,
	"BuildSuite Accountant": _FULL,
	"BuildSuite Site Engineer": _PETTY_CASH_SITE,
	"BuildSuite Foreman": _PETTY_CASH_SITE,
	"BuildSuite Store Keeper": _RAISE,  # raises petty-cash requests (create + read); no edit/disburse
	"BuildSuite Procurement Officer": _RAISE,  # raises petty-cash requests (create + read)
	"BuildSuite Estimator": _RAISE,  # raises petty-cash requests (create + read)
	"BuildSuite HR Manager": _RAISE,  # raises petty-cash requests (create + read)
	"BuildSuite QS": _READ,
}
PETTY_CASH_DISBURSE_ROLES = (
	"BuildSuite Accountant",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Administrator",
)


# Expense Entry (petty-cash / other spend). Site roles raise a draft (which counts
# as "pending approval"); finance roles submit it, which posts the Journal Entry.
# So submit/cancel is held by the finance approvers only, mirroring petty cash.
_EXPENSE_ENTRY_DRAFT = {"read": 1, "write": 1, "create": 1, "report": 1, "print": 1}
EXPENSE_ENTRY_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Director": _FULL_SUB,
	"BuildSuite PM": _FULL_SUB,
	"BuildSuite Accountant": _FULL_SUB,
	"BuildSuite Site Engineer": _EXPENSE_ENTRY_DRAFT,
	"BuildSuite Foreman": _EXPENSE_ENTRY_DRAFT,
	"BuildSuite Store Keeper": _RAISE,  # raises expense entries (create + read); finance approves/submits
	"BuildSuite Procurement Officer": _RAISE,  # raises expense entries (create + read)
	"BuildSuite QS": _RAISE,  # raises expense entries (create + read), per the QS ruling
	"BuildSuite Estimator": _RAISE,  # raises expense entries (create + read)
	"BuildSuite HR Manager": _RAISE,  # raises expense entries (create + read)
}


def setup_petty_cash_permissions():
	_apply_role_perms("Petty Cash Request", PETTY_CASH_ROLE_PERMS)
	_apply_role_perms("Expense Entry", EXPENSE_ENTRY_ROLE_PERMS, _SUBMIT_PTYPES)
	# The disburse / expense Journal Entry + its account picker read accounting masters.
	_read = {role: _READ for role in PETTY_CASH_DISBURSE_ROLES}
	for dt in ("Account", "Journal Entry"):
		_apply_role_perms(dt, _read)


def setup_subcontract_permissions():
	# Subcontractors are native Suppliers (supplier_type="Subcontractor") — grant the
	# BuildSuite roles CRUD on Supplier so the Vue "Subcontractor" screens work.
	_apply_role_perms("Supplier", SUBCONTRACT_ROLE_PERMS)
	_apply_role_perms("Subcontractor Work Order", SUBCONTRACT_WO_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Measurement Book", MEASUREMENT_BOOK_ROLE_PERMS)
	_apply_role_perms("Subcontractor Bill", SUBCONTRACT_BILL_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Construction Trade", SUBCONTRACT_MASTER_ROLE_PERMS, _SELECT_PTYPES)
	_apply_role_perms("Subcontract Delivery Type", SUBCONTRACT_MASTER_ROLE_PERMS, _SELECT_PTYPES)
	# The bill's billing pickers (expense account, tax template, withholding category) read
	# ERPNext's accounting masters — grant the finance-facing BuildSuite roles read so the
	# Vue dropdowns populate for non-admin personas.
	_billing_roles = _BILL_FULL_ROLES + ("BuildSuite Accountant",)
	# Account keeps read (it has a Finance Accounts screen + the disburse/JE context reads it).
	_apply_role_perms("Account", {role: _READ for role in _billing_roles})
	# The tax-template masters are pure billing-picker targets (no screen) — select, not read.
	_billing_select = {role: _SELECT for role in _billing_roles}
	for dt in ("Purchase Taxes and Charges Template", "Tax Category", "Tax Withholding Category"):
		_apply_role_perms(dt, _billing_select, _SELECT_PTYPES)


# --- M3 — Workforce -----------------------------------------------------------
# Field Attendance is the muster (submittable): Site Engineer + Foreman submit at
# site; HR Manager has the same rights for office-side correction; PM full; Director
# + Accountant read. Estimator / QS / Procurement / Store Keeper have no access.
FIELD_ATTENDANCE_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite PM": _FULL_SUB,
	"BuildSuite Site Engineer": _FULL_SUB,
	"BuildSuite Foreman": _FULL_SUB,
	"BuildSuite HR Manager": _FULL_SUB,
	"BuildSuite Director": _READ,
	"BuildSuite Accountant": _READ,
}
# Labour / Overtime Attendance are DERIVED registers — system-written when a Field
# Attendance is submitted. No role edits them directly (corrections go through cancel
# + amend on the muster), so every role that can see them is read-only.
DERIVED_ATTENDANCE_ROLE_PERMS = {
	role: _READ
	for role in (
		"BuildSuite Administrator",
		"BuildSuite Director",
		"BuildSuite PM",
		"BuildSuite QS",
		"BuildSuite Site Engineer",
		"BuildSuite Foreman",
		"BuildSuite Accountant",
		"BuildSuite HR Manager",
	)
}


# Worker master — the standard Employee doctype (BuildSuite has no separate Field Employee
# doctype). HR owns it; PM + admin tier full; Site Engineer edits (no delete); Director +
# Accountant + Foreman read. Employee is a linked-master read mirror already (every Project
# role reads it for owner/assignee pickers), so this only UPGRADES the writers — it must not
# revoke the pickers' read, hence _upgrade_role_perms.
EMPLOYEE_WRITE_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite PM": _FULL,
	"BuildSuite HR Manager": _FULL,
	"BuildSuite Site Engineer": _CRW,
}
# Crew — standalone labour-grouping master (not tied to a project). Foreman maintains
# membership day to day (edit, no delete); Site Engineer + PM + HR + admin tier full;
# Director reads. Crew Member is a child table and inherits Crew's perms.
CREW_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _FULL,
	"BuildSuite Site Engineer": _FULL,
	"BuildSuite Foreman": _CRW,
	"BuildSuite HR Manager": _FULL,
}


def setup_workforce_permissions():
	_apply_role_perms("Field Attendance", FIELD_ATTENDANCE_ROLE_PERMS, _SUBMIT_PTYPES)
	# Worker master + Crew (the M3 matrix missed both — Crew had no BuildSuite grant at all,
	# and Employee was read-only via the picker mirror, so HR/PM/admin couldn't maintain it).
	_upgrade_role_perms("Employee", EMPLOYEE_WRITE_ROLE_PERMS)
	_apply_role_perms("Crew", CREW_ROLE_PERMS)
	for dt in ("Labour Attendance Register", "Overtime Attendance Register"):
		# These registers historically shipped an over-broad `All` grant (write for every
		# user). The derived rule is "no role edits directly", so drop any `All` custom
		# grant before seeding the read-only BuildSuite matrix.
		frappe.db.delete("Custom DocPerm", {"parent": dt, "role": "All"})
		_apply_role_perms(dt, DERIVED_ATTENDANCE_ROLE_PERMS)


# --- M3 — Equipment -----------------------------------------------------------
# Machinery (the register) — Procurement + Store Keeper maintain it jointly
# (Procurement buys/hires, Store Keeper holds custody); PM may edit; Site Engineer +
# Foreman + Director + Accountant read. Non-submittable master, so CRWD is "full".
MACHINERY_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite Procurement Officer": _FULL,
	"BuildSuite Store Keeper": _FULL,
	"BuildSuite PM": _CRW,
	"BuildSuite Director": _READ,
	"BuildSuite Site Engineer": _READ,
	"BuildSuite Foreman": _READ,
	"BuildSuite Accountant": _READ,
}
# Machinery Usage (the plant usage log) — the site records usage (Site Engineer +
# PM full, Foreman edits, Store Keeper holds custody); Procurement reads it as the
# basis for hire bills; Director + Accountant read. Non-submittable, so CRWD is full.
MACHINERY_USAGE_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite PM": _FULL,
	"BuildSuite Site Engineer": _FULL,
	"BuildSuite Store Keeper": _FULL,
	"BuildSuite Foreman": _CRW,
	"BuildSuite Director": _READ,
	"BuildSuite Procurement Officer": _READ,
	"BuildSuite Accountant": _READ,
}


# Machinery Type — the master the Machinery register's `machinery_type` picker resolves.
# Everyone who can see a machine reads its type; Procurement / Store Keeper / admin maintain
# the list. Without this the type dropdown is empty for every role (it had no grant at all).
MACHINERY_TYPE_ROLE_PERMS = {
	**{role: _READ for role in MACHINERY_ROLE_PERMS},
	"BuildSuite Administrator": _FULL,
	"BuildSuite Procurement Officer": _FULL,
	"BuildSuite Store Keeper": _FULL,
}


def setup_equipment_permissions():
	_apply_role_perms("Machinery", MACHINERY_ROLE_PERMS)
	_apply_role_perms("Machinery Usage", MACHINERY_USAGE_ROLE_PERMS)
	_apply_role_perms("Machinery Type", MACHINERY_TYPE_ROLE_PERMS)


# --- M3 — Project Finance (customer-side money) -------------------------------
# Sales Invoice (money in) — Director + Accountant raise and submit; PM + QS read
# for billing context. Native ERPNext doctype: BuildSuite DocPerms overlay ERPNext's
# own Accounts roles (which keep their native access).
SALES_INVOICE_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Director": _FULL_SUB,
	"BuildSuite Accountant": _FULL_SUB,
	"BuildSuite PM": _READ,
	"BuildSuite QS": _READ,
	"BuildSuite Estimator": _READ,  # read-only billing context (per the Estimator ruling)
}
# Payment Entry (money movement) — Accountant + admin tier create and submit; it is
# created from the document being settled, never a blank form. Director + PM +
# Procurement read (Procurement to know what is already paid).
PAYMENT_ENTRY_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL_SUB,
	"BuildSuite Accountant": _FULL_SUB,
	"BuildSuite Director": _READ,
	"BuildSuite PM": _READ,
	"BuildSuite Procurement Officer": _READ,
	"BuildSuite Estimator": _READ,  # read-only (customer advances context, per the Estimator ruling)
}


# Customer — the commercial master. Director + Accountant + admin tier maintain it fully
# (incl. delete); PM edits (no delete). It's a linked-master read mirror (every Project role
# reads it for the client picker), so upgrade only the writers without revoking pickers' read.
CUSTOMER_WRITE_ROLE_PERMS = {
	"BuildSuite Administrator": _FULL,
	"BuildSuite Director": _FULL,
	"BuildSuite Accountant": _FULL,
	"BuildSuite PM": _CRW,
}


def setup_project_finance_permissions():
	_apply_role_perms("Sales Invoice", SALES_INVOICE_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Payment Entry", PAYMENT_ENTRY_ROLE_PERMS, _SUBMIT_PTYPES)
	# Customer was read-only for everyone via the picker mirror, so even admins couldn't
	# delete it. Upgrade the commercial writers on top of that mirror.
	_upgrade_role_perms("Customer", CUSTOMER_WRITE_ROLE_PERMS)
	setup_project_finance_report_access()


# The Project Finance workspace opens ERPNext's General Ledger + Profit and Loss Statement
# through the in-app renderer. run_report gates on BOTH the report's own roles (Accounts User/
# Manager/Auditor) and report permission on the ref doctype (GL Entry) — neither of which the
# BuildSuite finance personas have, so the reports 403 for them. Grant both.
_PF_ERPNEXT_REPORTS = ("General Ledger", "Profit and Loss Statement")
_PF_REPORT_ROLES = (
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite QS",
	"BuildSuite Accountant",
)


def setup_project_finance_report_access():
	"""Let the BuildSuite finance personas run the ERPNext reports the Project Finance tiles use.
	Re-applied every after_migrate: ERPNext's standard-report sync rewrites the report roles, so
	this self-heals."""
	# Report roles — standard reports can't be doc.save()d (developer-mode guard), so add the
	# Has Role child rows directly.
	for report in _PF_ERPNEXT_REPORTS:
		if not frappe.db.exists("Report", report):
			continue
		for role in _PF_REPORT_ROLES:
			if frappe.db.exists("Role", role) and not frappe.db.exists(
				"Has Role", {"parenttype": "Report", "parent": report, "role": role}
			):
				frappe.get_doc(
					{
						"doctype": "Has Role",
						"parenttype": "Report",
						"parentfield": "roles",
						"parent": report,
						"role": role,
					}
				).insert(ignore_permissions=True)
	# Read + report on GL Entry (the reports' ref doctype), layered on ERPNext's own perms.
	_upgrade_role_perms("GL Entry", {role: _READ for role in _PF_REPORT_ROLES})


def _ensure_workflow_state(name):
	if not frappe.db.exists("Workflow State", name):
		frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": name}).insert(
			ignore_permissions=True
		)


def _ensure_workflow_action(name):
	if not frappe.db.exists("Workflow Action Master", name):
		frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": name}).insert(
			ignore_permissions=True
		)


def setup_subcontractor_wo_workflow():
	"""The Work Order is now natively submittable (docstatus: Draft → Submitted → Cancelled +
	Amend), so the old approval Workflow is retired. Delete it idempotently — migrate keeps it
	gone even if a stale record survives."""
	if frappe.db.exists("Workflow", "Subcontractor Work Order Approval"):
		frappe.delete_doc(
			"Workflow", "Subcontractor Work Order Approval", ignore_permissions=True, force=True
		)


# Core/system doctypes never auto-granted by the read mirror, even if a BuildSuite doctype
# links to them — read here would be an over-grant, not a display convenience.
_READ_MIRROR_DENYLIST = {
	"User",
	"Role",
	"DocType",
	"DocField",
	"DocPerm",
	"Custom DocPerm",
	"Custom Field",
	"Property Setter",
	"Workflow",
	"Print Format",
	"Report",
	"Page",
	"File",
	"Server Script",
	"Client Script",
	"Webhook",
	"Email Account",
}


def setup_child_table_read_access():
	"""Grant each BuildSuite role read on the doctypes REFERENCED by every parent it can read —
	the parent's child (Table) doctypes AND its Link-field targets.

	Custom DocPerms completely override standard perms, so a role granted read on a parent has
	NO grant on the child tables or linked masters that parent's list/detail views render (line
	items, a `trade` → Labour Trade column, a filter dropdown, …) — and the fetch then 403s
	(e.g. HR Manager reads Crew but not its `trade` → Labour Trade). Mirroring read to those
	referenced doctypes closes that class of gap. Read only (never write/delete), layered on top
	of existing perms, system doctypes excluded — idempotent."""
	# Parents = doctypes with a REAL perm-map grant, identified by print=1 (every perm shorthand
	# — _READ/_FULL/_RAISE/… — carries it). This deliberately excludes the mirror's OWN grants
	# (which set only read=1), so a re-run doesn't treat mirror-granted masters as parents and
	# fan out second-order — that's what keeps after_migrate fast.
	grants = frappe.get_all(
		"Custom DocPerm",
		filters={"read": 1, "print": 1, "permlevel": 0, "role": ["in", list(BUILDSUITE_ROLES)]},
		fields=["parent as doctype", "role"],
	)
	roles_by_parent = {}
	for g in grants:
		roles_by_parent.setdefault(g.doctype, set()).add(g.role)

	# desired[ref] = the roles that should be able to read `ref` (a child table or link target).
	desired = {}
	for parent, roles in roles_by_parent.items():
		if not frappe.db.exists("DocType", parent):
			continue
		meta = frappe.get_meta(parent)
		referenced = {df.options for df in meta.get_table_fields() if df.options}
		referenced |= {
			df.options
			for df in meta.get_link_fields()
			if df.options and df.options not in _READ_MIRROR_DENYLIST
		}
		for ref in referenced:
			desired.setdefault(ref, set()).update(roles)
	if not desired:
		return

	# Everything already read-granted on those refs, in ONE query — so a steady-state re-run
	# (after_migrate) does zero writes and stays fast enough to run on every migrate.
	have = {}
	for row in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": ["in", list(desired)], "permlevel": 0, "read": 1},
		fields=["parent as doctype", "role"],
	):
		have.setdefault(row.doctype, set()).add(row.role)

	for ref, roles in desired.items():
		missing = roles - have.get(ref, set())
		if not missing:
			continue
		if not frappe.db.exists("DocType", ref) or frappe.get_meta(ref).issingle:
			continue
		# ptypes=("read",) — grant read without disturbing any other permission on the target.
		_upgrade_role_perms(ref, {role: {"read": 1} for role in missing}, ptypes=("read",))


def setup_record_permissions():
	"""Seed roles + DocPerms for every BuildSuite-scoped doctype."""
	from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import repair_default_personas
	from buildsuite_core.buildsuite_core.doctype.workspace_setting.seed_workspace_reports import (
		seed_workspace_reports,
	)

	setup_project_permissions()
	setup_task_permissions()
	setup_schedule_snapshot_permissions()
	setup_work_package_permissions()
	setup_task_progress_entry_permissions()
	setup_stage_planning_permissions()
	setup_boq_permissions()
	setup_estimation_master_permissions()
	setup_purchase_stock_permissions()
	setup_linked_master_permissions()
	setup_subcontract_permissions()
	setup_sco_permissions()
	setup_petty_cash_permissions()
	setup_workforce_permissions()
	setup_equipment_permissions()
	setup_project_finance_permissions()
	_ensure_role(WORKFLOW_EDITOR_ROLE)
	setup_stage_planning_workflow()
	setup_subcontractor_wo_workflow()
	# Mirror read to child tables of everything the BuildSuite roles can read (must run AFTER
	# all the parent grants above are in place).
	setup_child_table_read_access()
	# Personas map to the roles ensured above. Use repair (not plain seed) so an existing
	# persona that was created empty — the persona-creation patches run BEFORE the roles
	# exist, and plain seed_personas skips already-created personas — gets its missing
	# default roles backfilled now that the roles are in place.
	repair_default_personas()
	# Per-workspace report tiles (Query Reports + the Workspace Setting table).
	seed_workspace_reports()
