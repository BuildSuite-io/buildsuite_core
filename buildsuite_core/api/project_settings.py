# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Two-level Project page-tab visibility.

Level 1 — the site-wide template: the `Project Settings` Single's `tab_defaults` (one Project Tab
Visibility row per toggleable tab). Level 2 — a per-project override: the project's sparse
`custom_tab_overrides` (a row only where the project explicitly Shows/Hides a tab; absent = inherit).

The tab CATALOGUE (ids + labels + descriptions) is the SPA's `frontend/src/data/projectTabs.js`;
the backend keeps the minimal id→label list here only to seed defaults and label stored rows.
Overview is always shown and is never a toggle."""

import frappe
from frappe import _

SETTINGS = "Project Settings"
CHILD = "Project Tab Visibility"

# (tab id, label) for the toggleable tabs — mirrors frontend/src/data/projectTabs.js. Overview is
# deliberately absent (always shown; the fallback tab).
PROJECT_TABS = (
	("subprojects", "Subprojects"),
	("work-packages", "Work Packages"),
	("tasks", "Tasks"),
	("stage-planning", "Stage Planning"),
	("boq", "BOQ"),
	("scos", "Scope Changes"),
	("attachments", "Attachments"),
	("team", "Team"),
)
_LABELS = dict(PROJECT_TABS)
_ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}


def _require_admin():
	if not (_ADMIN_ROLES & set(frappe.get_roles())):
		frappe.throw(
			_("Editing Project Settings requires the Administrator or BuildSuite Administrator role."),
			frappe.PermissionError,
		)


def _rows(parenttype, parentfield, parent):
	"""Child visibility rows as {tab: bool}. frappe.get_all bypasses permission — the tab template
	is not sensitive and every user needs it to resolve which tabs their project view shows."""
	rows = frappe.get_all(
		CHILD,
		filters={"parenttype": parenttype, "parentfield": parentfield, "parent": parent},
		fields=["tab", "shown"],
	)
	return {r.tab: bool(r.shown) for r in rows}


# --------------------------------------------------------------------------- #
# Level 1 — site-wide template
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_project_settings():
	"""The tab template: {tabs: {tabId: shown}}. Any signed-in user (the project view resolves
	visibility against it)."""
	return {"tabs": _rows(SETTINGS, "tab_defaults", SETTINGS)}


@frappe.whitelist()
def set_project_settings(tabs=None):
	"""Replace the tab template. Admin only. `tabs` = {tabId: shown}; a tab absent from the map is
	treated as shown."""
	_require_admin()
	tabs = frappe.parse_json(tabs) or {}
	doc = frappe.get_single(SETTINGS)
	doc.set("tab_defaults", [])
	for tab_id, label in PROJECT_TABS:
		doc.append("tab_defaults", {"tab": tab_id, "label": label, "shown": 1 if tabs.get(tab_id, True) else 0})
	doc.flags.ignore_permissions = True
	doc.save()
	return get_project_settings()


def seed_project_settings():
	"""Seed the template with every toggleable tab shown, create-if-missing (leaves an admin's
	edits alone). Called on install + a one-time patch for existing sites."""
	if not frappe.db.exists("DocType", SETTINGS):
		return
	doc = frappe.get_single(SETTINGS)
	have = {r.tab for r in doc.tab_defaults}
	added = False
	for tab_id, label in PROJECT_TABS:
		if tab_id not in have:
			doc.append("tab_defaults", {"tab": tab_id, "label": label, "shown": 1})
			added = True
	if added:
		doc.flags.ignore_permissions = True
		doc.save()


# --------------------------------------------------------------------------- #
# Level 2 — per-project override
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_project_tab_overrides(project):
	"""A project's sparse overrides: {tabId: shown} for tabs it explicitly Shows/Hides."""
	return _rows("Project", "custom_tab_overrides", project)


@frappe.whitelist()
def set_project_tab_overrides(project, overrides=None):
	"""Replace a project's overrides. Requires Project write. `overrides` = {tabId: bool} carrying
	only explicit Show/Hide entries (a tab left on Default is omitted)."""
	if not frappe.has_permission("Project", "write", doc=project):
		frappe.throw(_("You don't have permission to edit this project."), frappe.PermissionError)
	overrides = frappe.parse_json(overrides) or {}
	doc = frappe.get_doc("Project", project)
	doc.set("custom_tab_overrides", [])
	for tab_id, shown in overrides.items():
		if tab_id in _LABELS and isinstance(shown, bool):
			doc.append("custom_tab_overrides", {"tab": tab_id, "label": _LABELS[tab_id], "shown": 1 if shown else 0})
	doc.flags.ignore_permissions = True  # write already checked above
	doc.save()
	return get_project_tab_overrides(project)
