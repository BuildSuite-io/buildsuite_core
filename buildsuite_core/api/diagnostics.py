# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Self-service diagnostics for 'the BuildSuite app icon isn't showing'.

The icon lives on several independent surfaces, each with its own gate, and which one applies
depends on the Frappe version:
  * the /apps launcher grid  -> the `add_to_apps_screen` hook + the setup-wizard filter + the logo
  * the new 16.5x desk Dock + per-module Sidebar fixtures
  * the legacy desk Workspace (its `app` field)

This endpoint gathers the server-side state of all of them in one read so an admin can paste it
back without SSH / Desk access. Read-only; admin-gated. Every section is independently guarded so a
differing remote version can never 500 the whole report — a failing section reports its error.
"""

import os

import frappe

APP = "buildsuite_core"
ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(frappe._("Only an administrator can read diagnostics."), frappe.PermissionError)


def _safe(fn):
	"""Run a gather step, returning its value or a captured error string (never raising)."""
	try:
		return fn()
	except Exception as e:  # a diagnostic must survive any one section failing
		return {"error": f"{type(e).__name__}: {e}"}


@frappe.whitelist()
def app_icon_diagnostics():
	"""Everything relevant to why the BuildSuite app icon may or may not appear, on any surface."""
	_require_admin()
	return {
		"generated_at": frappe.utils.now(),
		"site": frappe.local.site,
		"user": frappe.session.user,
		"user_roles": sorted(set(frappe.get_roles())),
		"is_system_manager": "System Manager" in frappe.get_roles(),
		"versions": _safe(_versions),
		"apps_screen": _safe(_apps_screen),
		"logo_asset": _safe(_logo_asset),
		"new_nav": _safe(_new_nav),
		"legacy_workspace": _safe(_legacy_workspace),
		"hints": _safe(_hints),
	}


def _versions():
	installed = frappe.get_installed_apps()
	out = {"installed_apps": installed, "app_versions": {}}
	for app in ("frappe", "erpnext", APP):
		try:
			out["app_versions"][app] = frappe.get_attr(f"{app}.__version__")
		except Exception:
			out["app_versions"][app] = None
	return out


def _apps_screen():
	"""The /apps launcher grid — governed by the add_to_apps_screen hook + the setup-wizard filter."""
	out = {}
	# The raw hook the app ships. Empty list => the app will NOT appear on /apps (this is the fix
	# PR #396 made by uncommenting add_to_apps_screen in hooks.py).
	out["add_to_apps_screen_hook"] = frappe.get_hooks("add_to_apps_screen", app_name=APP)

	# What get_apps() actually returns for THIS user (what the launcher shows).
	try:
		from frappe.apps import get_apps

		apps = get_apps()
		out["get_apps_names"] = [a.get("name") for a in apps]
		out["buildsuite_in_get_apps"] = APP in out["get_apps_names"]
		out["buildsuite_entry"] = next((a for a in apps if a.get("name") == APP), None)
	except Exception as e:  # broad on purpose: a diagnostic must not raise
		out["get_apps_error"] = f"{type(e).__name__}: {e}"

	# Non-System-Manager users only see apps that completed, or don't require, the setup wizard.
	for name, path in (
		("setup_wizard_completed_apps", "frappe.apps.get_setup_wizard_completed_apps"),
		("setup_wizard_not_required_apps", "frappe.apps.get_setup_wizard_not_required_apps"),
	):
		try:
			vals = list(frappe.get_attr(path)())
			out[name] = vals
			out[f"buildsuite_in_{name}"] = APP in vals
		except Exception as e:  # broad on purpose: a diagnostic must not raise
			out[name] = f"{type(e).__name__}: {e}"

	# The app-permission gate the launcher entry is filtered by (has_permission in the hook).
	try:
		from buildsuite_core.api.permission import _has_app_permission

		out["has_app_permission"] = _has_app_permission(log_denial=False)
	except Exception as e:  # broad on purpose: a diagnostic must not raise
		out["has_app_permission"] = f"{type(e).__name__}: {e}"
	return out


def _logo_asset():
	"""The icon file the launcher entry points at — present in the app source AND, critically,
	built into the served assets (a remote that never ran `bench build` serves a 404 -> no icon)."""
	url = "/assets/buildsuite_core/images/bs-icon.svg"
	out = {"expected_url": url}
	# Shipped in the app source?
	try:
		src = frappe.get_app_path(APP, "public", "images", "bs-icon.svg")
		out["source_path"] = src
		out["source_exists"] = os.path.exists(src)
	except Exception as e:  # broad on purpose: a diagnostic must not raise
		out["source_error"] = f"{type(e).__name__}: {e}"
	# Served from the built assets? (what the browser actually fetches)
	try:
		bench = frappe.utils.get_bench_path()
		served = os.path.join(bench, "sites", "assets", "buildsuite_core", "images", "bs-icon.svg")
		out["served_path"] = served
		out["served_exists"] = os.path.exists(served)
	except Exception as e:  # broad on purpose: a diagnostic must not raise
		out["served_error"] = f"{type(e).__name__}: {e}"
	return out


def _new_nav():
	"""The 16.5x desk Dock (app launcher) + per-module Sidebar fixtures (PR #395)."""
	out = {}
	out["dock_doctype_exists"] = bool(frappe.db.exists("DocType", "Dock"))
	out["sidebar_doctype_exists"] = bool(frappe.db.exists("DocType", "Sidebar"))
	if out["dock_doctype_exists"]:
		out["buildsuite_dock"] = frappe.db.get_value("Dock", APP, ["name", "app", "standard"], as_dict=True)
	if out["sidebar_doctype_exists"]:
		out["buildsuite_sidebar"] = frappe.db.get_value(
			"Sidebar", "BuildSuite", ["name", "app", "module", "standard"], as_dict=True
		)
	return out


def _legacy_workspace():
	"""The legacy desk Workspace 'BuildSuite' (its `app` field — the stray-backtick bug, PR #394).
	On 16.5x the field is gone / derived from the module; reported either way."""
	if not frappe.db.exists("Workspace", "BuildSuite"):
		return {"exists": False}
	row = frappe.db.get_value(
		"Workspace", "BuildSuite", ["name", "module", "public", "is_hidden"], as_dict=True
	)
	# `app` may not be a column on this Frappe version — read it defensively.
	try:
		row["app"] = frappe.db.get_value("Workspace", "BuildSuite", "app")
	except Exception:
		row["app"] = "(no app field on this version)"
	row["exists"] = True
	return row


def _hints():
	"""Plain-language read of the most common causes, derived from the sections above."""
	hints = []
	hook = frappe.get_hooks("add_to_apps_screen", app_name=APP)
	if not hook:
		hints.append(
			"add_to_apps_screen hook is EMPTY — the app won't appear on the /apps grid. The code "
			"that enables it (PR #396) is likely not deployed to this site."
		)
	served = None
	try:
		bench = frappe.utils.get_bench_path()
		served = os.path.exists(
			os.path.join(bench, "sites", "assets", "buildsuite_core", "images", "bs-icon.svg")
		)
	except Exception:
		served = None
	if served is False:
		hints.append(
			"The logo asset is NOT in the built assets — run `bench build --app buildsuite_core` on "
			"the remote. A missing asset shows a broken/absent icon even when the entry is listed."
		)
	if frappe.db.exists("DocType", "Dock") and not frappe.db.exists("Dock", APP):
		hints.append(
			"New-navigation Dock for buildsuite_core is MISSING — the left-rail app icon won't show. "
			"The Dock/Sidebar fixtures (PR #395) are likely not deployed, or migrate hasn't run."
		)
	if not hints:
		hints.append(
			"No obvious server-side cause found — the entry, logo and fixtures look present. Check a "
			"hard refresh / cleared cache in the browser, and that `bench build` + `bench migrate` ran."
		)
	return hints
