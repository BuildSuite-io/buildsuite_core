# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Settings pages declared by installed apps.

A settings page is a Single DocType. An extension app lists it in its own hooks.py:

    buildsuite_settings_pages = [
        {
            "doctype": "Acme Settings",          # must be a Single DocType
            "group": "Acme",                     # tile group on the Settings page
            "label": "Acme settings",
            "description": "Defaults for the Acme module",
            "icon": "settings",                  # optional
        },
    ]

Core shows it as a tile and renders it with the generic form at /settings/doc/<DocType>. Nothing
in the extension needs JavaScript. Visibility follows Frappe permissions: a user sees the tile only
when they can read the DocType, and saving is gated by its own DocPerms."""

import frappe


def get_settings_pages() -> list[dict]:
	"""The declared pages that are valid Single DocTypes the current user can read."""
	pages, seen = [], set()
	for raw in frappe.get_hooks("buildsuite_settings_pages") or []:
		if not isinstance(raw, dict):
			continue
		doctype = raw.get("doctype")
		if not doctype or doctype in seen or not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.get_meta(doctype).issingle:
			continue
		if not frappe.has_permission(doctype, "read"):
			continue
		seen.add(doctype)
		pages.append(
			{
				"doctype": doctype,
				"group": str(raw.get("group") or "Extensions"),
				"label": str(raw.get("label") or doctype),
				"description": str(raw.get("description") or ""),
				"icon": raw.get("icon") or None,
			}
		)
	return pages
