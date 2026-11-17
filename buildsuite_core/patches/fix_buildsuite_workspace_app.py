"""Repair the BuildSuite desk Workspace's corrupted `app` value.

The workspace fixture shipped with a stray trailing backtick — ``app = "buildsuite_core`"`` —
since the "Added BS sidebar" commit. Frappe 16.50 groups/filters the desk left-sidebar workspaces
by their `app` against the installed apps and drops any whose `app` matches no installed app — so
the BuildSuite workspace and its icon vanish from the desk sidebar. Set it back to the real app
name. Idempotent.

On Frappe 16.5x the Workspace `app` FIELD was removed (the app is derived from the workspace's
module instead), so the bug cannot occur there and there is nothing to repair — this patch no-ops.
It also reads/writes the column with raw SQL so a build whose meta no longer lists `app` can't
reject the query and break migrate.
"""

import frappe


def execute():
	# 16.5x removed the column — nothing to repair, and querying a missing column would abort migrate.
	if not frappe.db.has_column("Workspace", "app"):
		return
	# Raw SQL (not get_all / set_value) so a meta that no longer lists `app` doesn't reject it.
	rows = frappe.db.sql("select name, app from `tabWorkspace`", as_dict=True)
	for row in rows:
		app = row.app or ""
		# A trailing backtick (or any stray character) means app != "buildsuite_core" but still
		# starts with it; normalise those back.
		if app != "buildsuite_core" and app.startswith("buildsuite_core"):
			frappe.db.sql("update `tabWorkspace` set app = %s where name = %s", ("buildsuite_core", row.name))
			print(f"fix_buildsuite_workspace_app: {row.name} app {row.app!r} -> 'buildsuite_core'")
	frappe.clear_cache()
