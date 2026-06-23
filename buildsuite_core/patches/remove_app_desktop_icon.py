# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Remove the auto-generated "App" desktop icon for BuildSuite Core.

	When hooks.py still declared `add_to_apps_screen`, Frappe's
	`create_desktop_icons_from_installed_apps` created a Desktop Icon
	(icon_type="App", app="buildsuite_core") that shows on the /apps launcher.
	Commenting out the hook stops new icons being created but leaves the existing
	record on already-installed sites, where it duplicates the desktop icon set
	up manually.

	Delete only the App-type icon for this app — any Link/Folder icon (e.g. the
	manual "/core" shortcut) is left untouched. Idempotent, and a no-op on sites
	that never had the app icon (fresh installs, or sites already cleaned up).
	"""
	frappe.db.delete("Desktop Icon", {"icon_type": "App", "app": "buildsuite_core"})

	# Desktop icons are cached per user (`frappe.cache.hget("desktop_icons", user)`);
	# drop the cache so the removal shows without a restart.
	frappe.cache.delete_key("desktop_icons")
