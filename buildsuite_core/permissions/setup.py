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
	"BuildSuite Director": _READ,
	"BuildSuite PM": _READ,
	"BuildSuite Procurement Officer": _READ,
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


def _ensure_role(role_name):
	if not frappe.db.exists("Role", role_name):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role_name,
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)


def _apply_role_perms(doctype, role_perms, ptypes=_PTYPES):
	if not frappe.db.exists("DocType", doctype):
		return
	from frappe.permissions import add_permission, update_permission_property

	# The matrix is the single source of truth: drop any stale custom grant for a
	# BuildSuite role no longer listed (e.g. a role dropped from an earlier read
	# mirror), so removing a role from a matrix actually revokes its access.
	for role in set(BUILDSUITE_ROLES) - set(role_perms):
		frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role})

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
	_apply_role_perms("UOM", {role: _READ for role in _UOM_READ_ROLES})


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
}
# Trade / Delivery Type masters — read for everyone in the module, write for
# procurement + admins (they're resolved by the WO link pickers).
SUBCONTRACT_MASTER_ROLE_PERMS = {
	**{role: _READ for role in _SUBCONTRACT_FULL_ROLES + _SUBCONTRACT_READ_ROLES},
	"BuildSuite Procurement Officer": _FULL,
	"BuildSuite Administrator": _FULL,
}
# Measurement Book — the QS + Site Engineer record and certify site measurements,
# so they get full CRUD here (they only read the WO/Subcontractor masters).
_MB_FULL_ROLES = _SUBCONTRACT_FULL_ROLES + ("BuildSuite QS", "BuildSuite Site Engineer")
MEASUREMENT_BOOK_ROLE_PERMS = {
	**{role: _FULL for role in _MB_FULL_ROLES},
	"BuildSuite Accountant": _READ,
}
# Subcontractor Bill (RA Bill) — submittable. The QS + subcontract full roles raise and
# submit progress bills; the Accountant + Site Engineer read them.
_BILL_FULL_ROLES = _SUBCONTRACT_FULL_ROLES + ("BuildSuite QS",)
SUBCONTRACT_BILL_ROLE_PERMS = {
	**{role: _FULL_SUB for role in _BILL_FULL_ROLES},
	"BuildSuite Accountant": _READ,
	"BuildSuite Site Engineer": _READ,
}

# Subcontractor Work Order Approval workflow (status is the workflow state field).
_WO_CREATE_ROLES = _SUBCONTRACT_FULL_ROLES  # raise + submit a WO
_WO_APPROVE_ROLES = ("BuildSuite PM", "BuildSuite Director", "BuildSuite Administrator")
_WO_STATES = ("Draft", "Pending Approval", "Awarded", "In Progress", "Closed")
_WO_ACTIONS = ("Submit for Approval", "Approve", "Reject", "Start", "Close")
# (state, action, next_state, roles)
_WO_TRANSITIONS = (
	("Draft", "Submit for Approval", "Pending Approval", _WO_CREATE_ROLES),
	("Pending Approval", "Approve", "Awarded", _WO_APPROVE_ROLES),
	("Pending Approval", "Reject", "Draft", _WO_APPROVE_ROLES),
	("Awarded", "Start", "In Progress", _WO_CREATE_ROLES),
	("Awarded", "Close", "Closed", _WO_APPROVE_ROLES),
	("In Progress", "Close", "Closed", _WO_APPROVE_ROLES),
)


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
	"BuildSuite QS": _READ,
}
PETTY_CASH_DISBURSE_ROLES = (
	"BuildSuite Accountant",
	"BuildSuite Director",
	"BuildSuite PM",
	"BuildSuite Administrator",
)


def setup_petty_cash_permissions():
	_apply_role_perms("Petty Cash Request", PETTY_CASH_ROLE_PERMS)
	# The disburse Journal Entry + its account picker read accounting masters.
	_read = {role: _READ for role in PETTY_CASH_DISBURSE_ROLES}
	for dt in ("Account", "Journal Entry"):
		_apply_role_perms(dt, _read)


def setup_subcontract_permissions():
	# Subcontractors are native Suppliers (supplier_type="Subcontractor") — grant the
	# BuildSuite roles CRUD on Supplier so the Vue "Subcontractor" screens work.
	_apply_role_perms("Supplier", SUBCONTRACT_ROLE_PERMS)
	_apply_role_perms("Subcontractor Work Order", SUBCONTRACT_ROLE_PERMS)
	_apply_role_perms("Measurement Book", MEASUREMENT_BOOK_ROLE_PERMS)
	_apply_role_perms("Subcontractor Bill", SUBCONTRACT_BILL_ROLE_PERMS, _SUBMIT_PTYPES)
	_apply_role_perms("Construction Trade", SUBCONTRACT_MASTER_ROLE_PERMS)
	_apply_role_perms("Subcontract Delivery Type", SUBCONTRACT_MASTER_ROLE_PERMS)


def _ensure_workflow_state(name):
	if not frappe.db.exists("Workflow State", name):
		frappe.get_doc(
			{"doctype": "Workflow State", "workflow_state_name": name}
		).insert(ignore_permissions=True)


def _ensure_workflow_action(name):
	if not frappe.db.exists("Workflow Action Master", name):
		frappe.get_doc(
			{"doctype": "Workflow Action Master", "workflow_action_name": name}
		).insert(ignore_permissions=True)


def setup_subcontractor_wo_workflow():
	"""Build the Subcontractor Work Order Approval workflow. Draft is editable by any
	module user (DocPerm gates); later states are locked (edits via the workflow)."""
	if not frappe.db.exists("DocType", "Subcontractor Work Order"):
		return
	for s in _WO_STATES:
		_ensure_workflow_state(s)
	for a in _WO_ACTIONS:
		_ensure_workflow_action(a)

	name = "Subcontractor Work Order Approval"
	wf = frappe.get_doc("Workflow", name) if frappe.db.exists("Workflow", name) else frappe.new_doc(
		"Workflow"
	)
	wf.workflow_name = name
	wf.document_type = "Subcontractor Work Order"
	wf.workflow_state_field = "status"
	wf.is_active = 1
	wf.send_email_alert = 0
	wf.set("states", [])
	for s in _WO_STATES:
		wf.append(
			"states",
			{
				"state": s,
				"doc_status": "0",
				"allow_edit": WORKFLOW_EDITOR_ROLE if s == "Draft" else "System Manager",
			},
		)
	wf.set("transitions", [])
	for state, action, next_state, roles in _WO_TRANSITIONS:
		for role in roles:
			wf.append(
				"transitions",
				{
					"state": state,
					"action": action,
					"next_state": next_state,
					"allowed": role,
					"allow_self_approval": 1,
				},
			)
	wf.flags.ignore_permissions = True
	wf.save()


def setup_record_permissions():
	"""Seed roles + DocPerms for every BuildSuite-scoped doctype."""
	from buildsuite_core.buildsuite_core.doctype.persona.seed_personas import seed_personas
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
	_ensure_role(WORKFLOW_EDITOR_ROLE)
	setup_stage_planning_workflow()
	setup_subcontractor_wo_workflow()
	# Personas map to the roles ensured above — seed them once the roles exist.
	seed_personas()
	# Per-workspace report tiles (Query Reports + the Workspace Setting table).
	seed_workspace_reports()
