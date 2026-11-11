# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Frontend extension discovery.

An app extends the BuildSuite SPA by declaring, in its own hooks.py:

    buildsuite_frontend_extensions = [
        {
            "name": "acme",                              # unique, shown in diagnostics
            "js": "/assets/acme/js/extension.js",        # an ES module: export default register(sdk)
            "css": "/assets/acme/css/extension.css",     # optional
            "min_sdk": "1.0",                            # optional: oldest SDK it works with
        },
    ]

Frappe returns the hooks of INSTALLED apps only, so an extension is active on a site exactly when
its app is installed there. The boot payload carries the result to the SPA, which loads each entry
at runtime (frontend/src/sdk/loader.js)."""

import frappe

# Bump the major when the public surface changes incompatibly, the minor when it only grows.
# The JS SDK carries the same number (frontend/src/sdk/index.js).
SDK_VERSION = "1.0"


def _is_asset_path(path) -> bool:
	"""Only files served from an app's /assets folder: no external hosts, no traversal."""
	return isinstance(path, str) and path.startswith("/assets/") and ".." not in path and "//" not in path


def get_extension_entries() -> list[dict]:
	"""The valid, de-duplicated extension entries of the apps installed on this site."""
	entries, seen = [], set()
	for raw in frappe.get_hooks("buildsuite_frontend_extensions") or []:
		if not isinstance(raw, dict):
			continue
		name, js = raw.get("name"), raw.get("js")
		if not name or name in seen or not _is_asset_path(js):
			continue
		css = raw.get("css")
		seen.add(name)
		entries.append(
			{
				"name": str(name),
				"js": js,
				"css": css if _is_asset_path(css) else None,
				"min_sdk": str(raw["min_sdk"]) if raw.get("min_sdk") else None,
			}
		)
	return entries
