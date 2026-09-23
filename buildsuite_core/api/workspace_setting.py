# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for the per-workspace shortcut tiles (Workspace Setting Single).
Two parallel groups, both tagged by workspace slug and configured in the Workspace Setting
screen:

- **Reports** — a tile's destination is an explicit `route` (an in-app path like
  `/subcontractor-work-orders`, or a Desk URL like `/app/query-report/Stock Balance`) or a
  linked Frappe `Report` (whose Desk route + name are derived when `route` is blank).
- **Records** — a tile points at an admin-curated DocType; it opens the generic /records
  list + add/edit form for that DocType. The list config (columns/search/sort) is derived
  from the DocType's own Frappe meta. The configured DocTypes form an allowlist that gates
  the generic list/form config endpoints (Frappe permissions still gate each record)."""

from urllib.parse import quote

import frappe
from frappe import _

from buildsuite_core.permissions.resource_map import route_doctype

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SETTINGS = "Workspace Setting"

# The live BuildSuite workspaces that expose a configurable Reports group.
WORKSPACES = (
	{"slug": "site-execution", "label": "Site Execution"},
	{"slug": "estimation", "label": "Estimation"},
	{"slug": "procurement", "label": "Procurement"},
	{"slug": "subcontract", "label": "Subcontract"},
	{"slug": "project-finance", "label": "Project Finance"},
	{"slug": "workforce", "label": "Workforce"},
)
_SLUGS = {w["slug"] for w in WORKSPACES}


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage settings."), frappe.PermissionError)


def _report_route(report_name):
	"""Route for a report tile. Query/Script Reports render IN-APP via the generic
	FrappeReport renderer (/reports/view/<name>); Report Builder reports have no in-app
	renderer, so they still open on the Desk."""
	meta = frappe.db.get_value("Report", report_name, ["report_type", "ref_doctype"], as_dict=True)
	if not meta:
		return None
	if meta.report_type in ("Query Report", "Script Report"):
		return f"/reports/view/{quote(report_name)}"
	doctype_route = frappe.scrub(meta.ref_doctype or "").replace("_", "-")
	return f"/app/{doctype_route}/view/report/{quote(report_name)}"


def _resolve(row):
	"""A stored row → a renderable tile, or None if it has no valid destination.
	Explicit `route` wins; otherwise derive route + label from the linked Report."""
	label = (row.get("label") or "").strip()
	route = (row.get("route") or "").strip()
	report = (row.get("report") or "").strip()
	if not route and report:
		if not frappe.db.exists("Report", report):
			return None
		# Hide the tile if the user can't run the report (the Report's own roles gate it) —
		# e.g. site roles don't see the finance-restricted Billing / Subcontractor reports.
		if not frappe.get_cached_doc("Report", report).is_permitted():
			return None
		route = _report_route(report)
		label = label or frappe.db.get_value("Report", report, "report_name") or report
	if not route:
		return None
	# A bespoke (custom-UI) report keeps its own `route`, but its access is anchored on a backend
	# Report record (buildsuite_core.report_access): hide the tile unless that anchor permits the
	# user. Routes with no anchor (plain navigation tiles) are unaffected.
	from buildsuite_core.report_access import is_route_permitted

	if not is_route_permitted(route):
		return None
	return {
		"label": label or route,
		"route": route,
		"icon": (row.get("icon") or "file-text").strip() or "file-text",
		"description": (row.get("description") or "").strip(),
		# External = a Desk URL or absolute link (opened via <a>, not the SPA router).
		"external": route.startswith("/app/") or "://" in route,
	}


@frappe.whitelist()
def get_workspace_reports(workspace: str):
	"""Ordered, renderable report tiles for a workspace. Any signed-in user (whoever
	can open the workspace)."""
	if workspace not in _SLUGS:
		return []
	settings = frappe.get_single(SETTINGS)
	out = []
	for row in settings.reports:
		if row.workspace != workspace:
			continue
		tile = _resolve(row.as_dict())
		if tile:
			out.append(tile)
	return out


@frappe.whitelist()
def get_workspace_settings():
	"""Every live workspace + its configured report and doctype rows, for the admin screen."""
	_require_admin()
	settings = frappe.get_single(SETTINGS)
	by_ws = {w["slug"]: [] for w in WORKSPACES}
	for row in settings.reports:
		if row.workspace in by_ws:
			by_ws[row.workspace].append(
				{
					"label": row.label or "",
					"report": row.report or "",
					"route": row.route or "",
					"icon": row.icon or "",
					"description": row.description or "",
				}
			)
	by_dt = {w["slug"]: [] for w in WORKSPACES}
	for row in settings.doctypes:
		if row.workspace in by_dt:
			by_dt[row.workspace].append(
				{
					"label": row.label or "",
					"doctype": row.document_type or "",
					"icon": row.icon or "",
					"description": row.description or "",
				}
			)
	return {"workspaces": list(WORKSPACES), "reports": by_ws, "doctypes": by_dt}


@frappe.whitelist()
def set_workspace_reports(workspace: str, reports: str | None = None):
	"""Replace one workspace's report rows (order preserved), leaving other
	workspaces' rows untouched. Admin only."""
	_require_admin()
	if workspace not in _SLUGS:
		frappe.throw(_("Unknown workspace: {0}").format(workspace))
	reports = frappe.parse_json(reports) or []
	settings = frappe.get_single(SETTINGS)

	# Preserve the other workspaces' rows; rebuild this workspace's from the payload.
	kept = [r for r in settings.reports if r.workspace != workspace]
	settings.set("reports", [])
	for r in kept:
		settings.append(
			"reports",
			{
				"workspace": r.workspace,
				"label": r.label,
				"report": r.report,
				"route": r.route,
				"icon": r.icon,
				"description": r.description,
			},
		)
	for row in reports:
		report = (row.get("report") or "").strip()
		route = (row.get("route") or "").strip()
		if not (report or route):
			continue
		settings.append(
			"reports",
			{
				"workspace": workspace,
				"label": (row.get("label") or "").strip(),
				"report": report,
				"route": route,
				"icon": (row.get("icon") or "").strip(),
				"description": (row.get("description") or "").strip(),
			},
		)
	settings.flags.ignore_permissions = True
	settings.save()
	return get_workspace_settings()


# --------------------------------------------------------------------------- #
# DocType shortcut tiles — the generic /records list + form for admin-curated
# DocTypes. Parallel to the report tiles above.
# --------------------------------------------------------------------------- #
# List fieldtypes that never belong as a list column even if flagged in_list_view.
_NON_LIST_FIELDTYPES = {"Table", "Table MultiSelect", "Section Break", "Column Break", "HTML", "Button"}
# Fieldtypes that make a usable list filter (discrete/enumerable or a simple text/date match).
_FILTERABLE_FIELDTYPES = {"Link", "Select", "Check", "Date", "Datetime", "Data", "Small Text"}


def _resolve_doctype(row):
	"""A stored doctype row → a renderable tile, or None. Hidden if the DocType is gone
	or the user can't read it (so a tile never leaks a DocType a persona has no access to)."""
	dt = (row.get("document_type") or "").strip()
	if not dt or not frappe.db.exists("DocType", dt):
		return None
	if not frappe.has_permission(dt, "read"):
		return None
	return {
		"label": (row.get("label") or "").strip() or dt,
		"doctype": dt,
		"route": f"/records/{quote(dt)}",
		"icon": (row.get("icon") or "file-text").strip() or "file-text",
		"description": (row.get("description") or "").strip(),
	}


def _allowed_doctypes():
	"""The allowlist: every DocType an admin has added to any workspace's Records group.
	The generic list/form config endpoints serve only these — the routes can't be turned
	into an open browser of arbitrary DocTypes (Frappe perms still gate each row too)."""
	settings = frappe.get_single(SETTINGS)
	return {r.document_type for r in settings.doctypes if r.document_type}


def _require_allowed(doctype):
	"""The generic list/form serves any DocType the user can READ — so search + deep links can
	reach the records of a doctype the SPA has no bespoke view for (the generic view is the
	universal fallback). Frappe's own read permission still gates the doctype and every row."""
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("{0} is not available here.").format(doctype or "DocType"), frappe.PermissionError)
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(
			_("You don't have access to {0}.").format(doctype), frappe.PermissionError
		)


@frappe.whitelist()
def get_workspace_doctypes(workspace: str):
	"""Ordered, renderable DocType tiles for a workspace. Any signed-in user."""
	if workspace not in _SLUGS:
		return []
	settings = frappe.get_single(SETTINGS)
	out = []
	for row in settings.doctypes:
		if row.workspace != workspace:
			continue
		tile = _resolve_doctype(row.as_dict())
		if tile:
			out.append(tile)
	return out


@frappe.whitelist()
def set_workspace_doctypes(workspace: str, doctypes: str | None = None):
	"""Replace one workspace's DocType rows (order preserved), leaving other workspaces'
	rows untouched. Admin only."""
	_require_admin()
	if workspace not in _SLUGS:
		frappe.throw(_("Unknown workspace: {0}").format(workspace))
	doctypes = frappe.parse_json(doctypes) or []
	settings = frappe.get_single(SETTINGS)

	kept = [r for r in settings.doctypes if r.workspace != workspace]
	settings.set("doctypes", [])
	for r in kept:
		settings.append(
			"doctypes",
			{
				"workspace": r.workspace,
				"label": r.label,
				"document_type": r.document_type,
				"icon": r.icon,
				"description": r.description,
			},
		)
	for row in doctypes:
		dt = (row.get("doctype") or "").strip()
		if not dt:
			continue
		settings.append(
			"doctypes",
			{
				"workspace": workspace,
				"label": (row.get("label") or "").strip(),
				"document_type": dt,
				"icon": (row.get("icon") or "").strip(),
				"description": (row.get("description") or "").strip(),
			},
		)
	settings.flags.ignore_permissions = True
	settings.save()
	return get_workspace_settings()


@frappe.whitelist()
def get_doctype_list_config(doctype: str):
	"""The DocTypeListView props for an allow-listed DocType, derived from its Frappe meta:
	columns from in_list_view fields, search from search_fields, order from sort_field."""
	_require_allowed(doctype)
	meta = frappe.get_meta(doctype)

	list_fields = [
		df.fieldname
		for df in meta.fields
		if df.in_list_view and df.fieldtype not in _NON_LIST_FIELDTYPES
	]
	if meta.title_field and meta.title_field not in list_fields:
		list_fields.insert(0, meta.title_field)
	field_order = ["name"] + [f for f in list_fields if f != "name"]

	search = [s.strip() for s in (meta.search_fields or "").split(",") if s.strip()]
	search_fields = ["name"] + [s for s in search if s != "name"]
	if meta.title_field and meta.title_field not in search_fields:
		search_fields.append(meta.title_field)

	order_by = f"{meta.sort_field or 'modified'} {(meta.sort_order or 'desc').lower()}"

	# Filter controls, derived from the DocType's own meta: Frappe's list filters
	# (in_standard_filter) plus the list columns (in_list_view), of filterable types.
	filters = []
	seen = set()
	for df in meta.fields:
		if df.fieldname in seen or df.fieldname == "name" or df.hidden:
			continue
		if df.fieldtype not in _FILTERABLE_FIELDTYPES:
			continue
		if not (df.in_standard_filter or df.in_list_view):
			continue
		seen.add(df.fieldname)
		filters.append(
			{
				"fieldname": df.fieldname,
				"label": df.label or df.fieldname,
				"fieldtype": df.fieldtype,
				"options": df.options or "",
			}
		)

	return {
		"doctype": doctype,
		"label": doctype,
		"fieldOrder": field_order,
		"searchFields": search_fields,
		"initialOrderBy": order_by,
		"titleField": meta.title_field or "name",
		"isSubmittable": bool(meta.is_submittable),
		"filters": filters,
	}


@frappe.whitelist()
def get_doctype_permissions(doctype: str):
	"""The current user's action permissions on an allow-listed DocType — for gating the
	New / Save / Delete buttons. Server-side enforcement is unchanged; this is UI only."""
	_require_allowed(doctype)
	return {
		"read": bool(frappe.has_permission(doctype, "read")),
		"write": bool(frappe.has_permission(doctype, "write")),
		"create": bool(frappe.has_permission(doctype, "create")),
		"delete": bool(frappe.has_permission(doctype, "delete")),
		"submit": bool(frappe.has_permission(doctype, "submit")),
		"cancel": bool(frappe.has_permission(doctype, "cancel")),
	}


@frappe.whitelist()
def submit_record(doctype: str, name: str):
	"""Submit a saved draft of an allow-listed DocType (doc.submit enforces the submit
	permission + validation server-side)."""
	_require_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def cancel_record(doctype: str, name: str):
	"""Cancel a submitted document of an allow-listed DocType."""
	_require_allowed(doctype)
	doc = frappe.get_doc(doctype, name)
	doc.cancel()
	return {"name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def amend_record(doctype: str, name: str):
	"""Amend a cancelled document — a fresh draft copy linked via amended_from."""
	_require_allowed(doctype)
	src = frappe.get_doc(doctype, name)
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled document can be amended."))
	new = frappe.copy_doc(src)
	new.amended_from = name
	new.insert()
	return {"name": new.name, "docstatus": new.docstatus}


@frappe.whitelist()
def get_visible_workspaces():
	"""The SPA sidebar workspaces the current user may see: the BuildSuite Workspace records
	whose Visible-To roles intersect the user's roles, in sort order.

	This is the backend source for sidebar / landing visibility + ordering (replacing the
	frontend WORKSPACE_VISIBILITY / WORKSPACE_ORDER matrices). Per-tile and per-record gating
	stay separate (usePermissions caps + get_doctype_permissions); this only decides which
	workspace entries appear."""
	if not frappe.db.exists("DocType", "BuildSuite Workspace"):
		return []

	user_roles = set(frappe.get_roles())
	# One pass for the role rows, grouped by workspace, so it's 2 queries not N+1.
	access_by_ws = {}
	for row in frappe.get_all("BuildSuite Workspace Role", fields=["parent", "role", "access"]):
		access_by_ws.setdefault(row.parent, {})[row.role] = row.access

	workspaces = frappe.get_all(
		"BuildSuite Workspace",
		fields=["name", "label", "icon", "route", "workspace_group", "sort_order", "description"],
		order_by="sort_order asc",
	)
	out = []
	for ws in workspaces:
		# The access hints of the roles the user actually holds on this workspace.
		hints = [access_by_ws[ws.name][r] for r in user_roles if r in access_by_ws.get(ws.name, {})]
		if not hints:
			continue
		out.append(
			{
				"slug": ws.name,
				"label": ws.label,
				"icon": ws.icon,
				"route": ws.route,
				"group": ws.workspace_group,
				"order": ws.sort_order,
				"description": ws.description or "",
				# The strongest hint among the user's roles (combined-responsibility users). Cosmetic.
				"access": max(hints, key=lambda h: _ACCESS_RANK.get(h, 0)),
			}
		)
	return out


# Precedence for the cosmetic access hint when a user holds several roles on one workspace.
_ACCESS_RANK = {
	"full": 6, "approve": 5, "create-own": 4, "mr-only": 3,
	"read": 2, "pay-only": 2, "self-service": 1, "team-only": 1,
}


# --------------------------------------------------------------------------- #
# Workspace quick-nav shortcuts (BuildSuite Workspace Shortcut) — the backend
# home of the former client-side workspaceStructure config. Role-gated per
# shortcut; an empty role list inherits the workspace's own visibility.
# --------------------------------------------------------------------------- #
def _shortcut_roles(names, parenttype):
	"""role-name sets grouped by parent, for the given child parenttype."""
	out = {}
	if not names:
		return out
	for row in frappe.get_all(
		"BuildSuite Workspace Role",
		filters={"parent": ["in", names], "parenttype": parenttype},
		fields=["parent", "role"],
	):
		out.setdefault(row.parent, set()).add(row.role)
	return out


@frappe.whitelist()
def get_workspace_shortcuts(workspace: str):
	"""Ordered quick-nav shortcuts for a workspace, filtered to the current user's roles. A
	shortcut with no roles inherits the workspace's visibility (shown to anyone who can see it).
	Returns [] if the user can't see the workspace at all."""
	if not frappe.db.exists("BuildSuite Workspace", workspace):
		return []
	user_roles = set(frappe.get_roles())
	ws_roles = set(
		frappe.get_all(
			"BuildSuite Workspace Role",
			filters={"parent": workspace, "parenttype": "BuildSuite Workspace"},
			pluck="role",
		)
	)
	if not (ws_roles & user_roles):
		return []

	shortcuts = frappe.get_all(
		"BuildSuite Workspace Shortcut",
		filters={"workspace": workspace, "enabled": 1},
		fields=["name", "label", "icon", "route", "sort_order"],
		order_by="sort_order asc",
	)
	roles_by_sc = _shortcut_roles([s.name for s in shortcuts], "BuildSuite Workspace Shortcut")
	out = []
	for s in shortcuts:
		restrict = roles_by_sc.get(s.name)
		if restrict and not (restrict & user_roles):
			continue  # restricted, and the user holds none of the allowed roles
		# Hide a shortcut that points at a DocType the user can't read — a role may see the
		# workspace yet lack read on one of its records (e.g. Procurement persona with Task
		# read revoked). Mirrors _resolve_doctype's gate for the curated DocType tiles; routes
		# with no doctype behind them (dashboards, schedule, reports) stay un-gated.
		dt = route_doctype(s.route)
		if dt and not frappe.has_permission(dt, "read"):
			continue
		out.append({"label": s.label, "icon": s.icon, "route": s.route, "order": s.sort_order})
	return out


@frappe.whitelist()
def get_workspace_shortcuts_config():
	"""Every BuildSuite workspace + its shortcut rows (incl. restrict-to role names), for the
	admin Workspace Structure screen."""
	_require_admin()
	workspaces = frappe.get_all(
		"BuildSuite Workspace",
		filters={"workspace_group": "buildsuite"},
		fields=["name", "label", "sort_order"],
		order_by="sort_order asc",
	)
	shortcuts = frappe.get_all(
		"BuildSuite Workspace Shortcut",
		fields=["name", "workspace", "label", "icon", "route", "sort_order", "enabled"],
		order_by="sort_order asc",
	)
	roles_by_sc = _shortcut_roles([s.name for s in shortcuts], "BuildSuite Workspace Shortcut")
	# Each workspace's own Visible-To roles = the set a shortcut may be restricted to.
	ws_roles = _shortcut_roles([w.name for w in workspaces], "BuildSuite Workspace")
	by_ws = {w.name: [] for w in workspaces}
	for s in shortcuts:
		if s.workspace not in by_ws:
			continue
		by_ws[s.workspace].append(
			{
				"label": s.label,
				"icon": s.icon,
				"route": s.route,
				"sort_order": s.sort_order,
				"enabled": bool(s.enabled),
				"roles": sorted(roles_by_sc.get(s.name, set())),
			}
		)
	return [
		{
			"slug": w.name,
			"label": w.label,
			"available_roles": sorted(ws_roles.get(w.name, set())),
			"shortcuts": by_ws[w.name],
		}
		for w in workspaces
	]


@frappe.whitelist()
def set_workspace_shortcuts(workspace: str, shortcuts: str | None = None):
	"""Replace one workspace's shortcut rows (order preserved). Admin only. `shortcuts` is a
	JSON list of {label, icon, route, sort_order, enabled, roles:[role names]}; empty roles =
	inherit the workspace's visibility."""
	_require_admin()
	if not frappe.db.exists("BuildSuite Workspace", workspace):
		frappe.throw(_("Unknown workspace: {0}").format(workspace))
	rows = frappe.parse_json(shortcuts) or []

	# Rebuild: drop this workspace's shortcuts, recreate from the payload.
	for name in frappe.get_all("BuildSuite Workspace Shortcut", filters={"workspace": workspace}, pluck="name"):
		frappe.delete_doc("BuildSuite Workspace Shortcut", name, ignore_permissions=True, force=True)
	for i, row in enumerate(rows):
		label = (row.get("label") or "").strip()
		route = (row.get("route") or "").strip()
		if not (label and route):
			continue
		roles = [{"role": r} for r in (row.get("roles") or []) if frappe.db.exists("Role", r)]
		doc = frappe.new_doc("BuildSuite Workspace Shortcut")
		doc.workspace = workspace
		doc.label = label
		doc.icon = (row.get("icon") or "🔗").strip() or "🔗"
		doc.route = route
		doc.sort_order = row.get("sort_order") if row.get("sort_order") is not None else i + 1
		doc.enabled = 1 if row.get("enabled", True) else 0
		doc.set("roles", roles)
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return get_workspace_shortcuts_config()
