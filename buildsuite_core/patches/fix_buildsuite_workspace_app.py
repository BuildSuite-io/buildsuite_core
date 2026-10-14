"""Repair the BuildSuite desk Workspace's corrupted `app` value.

The workspace fixture shipped with a stray trailing backtick — ``app = "buildsuite_core`"`` —
since the "Added BS sidebar" commit. Frappe groups/filters the desk left-sidebar workspaces by
their `app` against the installed apps; the lenient older desk still showed it, but Frappe 16.50's
stricter app filtering drops any workspace whose `app` matches no installed app — so the BuildSuite
workspace and its icon vanish from the desk sidebar. Set it back to the real app name. Idempotent.
"""

import frappe


def execute():
	# A trailing backtick (or any stray character) means app != "buildsuite_core" but still starts
	# with it; normalise those back. Matched in Python to avoid LIKE treating `_` as a wildcard.
	rows = frappe.get_all("Workspace", fields=["name", "app"])
	for row in rows:
		app = row.app or ""
		if app != "buildsuite_core" and app.startswith("buildsuite_core"):
			frappe.db.set_value("Workspace", row.name, "app", "buildsuite_core", update_modified=False)
			print(f"fix_buildsuite_workspace_app: {row.name} app {row.app!r} -> 'buildsuite_core'")
	frappe.clear_cache()
