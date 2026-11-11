# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Scaffold a BuildSuite extension app.

    bench new-buildsuite-extension acme_ext --title "Acme Extension"

writes a ready-to-install Frappe app that already declares the extension hook, ships a
runnable `register(sdk)` module and a stub settings page hook. No frontend build step is
needed: the SDK hands the extension Vue (`sdk.vue`), so the file is plain JavaScript."""

import re
from pathlib import Path

import frappe

from buildsuite_core.sdk.extensions import SDK_VERSION

_NAME = re.compile(r"^[a-z][a-z0-9_]{2,}$")


def _files(app: str, title: str, author: str, email: str) -> dict[str, str]:
	sdk_min = SDK_VERSION
	return {
		"pyproject.toml": f"""[project]
name = "{app}"
authors = [{{ name = "{author}", email = "{email}" }}]
description = "{title}: a BuildSuite Core extension"
requires-python = ">=3.14"
readme = "README.md"
dynamic = ["version"]
dependencies = []

[build-system]
requires = ["flit_core >=3.4,<4"]
build-backend = "flit_core.buildapi"
""",
		"README.md": f"""# {title}

A BuildSuite Core extension. Install it on a site that has `buildsuite_core`:

    bench get-app <path-or-url-of-this-app>
    bench --site <site> install-app {app}

Edit `{app}/public/js/extension.js` (the `register(sdk)` function) to add pages, slots,
workspace tiles, view overrides and DocType hooks. Declare settings pages and Custom Fields in
`{app}/hooks.py`. Reload the browser after changing the file; run `bench build --app {app}`
only if you add files under `public/`. See `docs/extension-sdk-plan.md` in buildsuite_core.
""",
		f"{app}/__init__.py": '__version__ = "0.0.1"\n',
		f"{app}/modules.txt": f"{title}\n",
		f"{app}/patches.txt": "",
		f"{app}/hooks.py": f'''app_name = "{app}"
app_title = "{title}"
app_publisher = "{author}"
app_description = "{title}: a BuildSuite Core extension"
app_email = "{email}"
app_license = "mit"

required_apps = ["buildsuite_core"]

# The SPA loads this module at runtime on every site where this app is installed.
buildsuite_frontend_extensions = [
	{{
		"name": "{app}",
		"js": "/assets/{app}/js/extension.js",
		"min_sdk": "{sdk_min}",
	}},
]

# Settings pages: Single DocTypes listed on the SPA Settings hub.
# buildsuite_settings_pages = [
# 	{{"doctype": "My Settings", "group": "{title}", "label": "My settings"}},
# ]

# Custom Fields shipped with the app (bind them on a form with sdk.doctype(...).on({{fields: [...]}})).
# fixtures = [{{"dt": "Custom Field", "filters": [["name", "in", ["Quotation-my_field"]]]}}]
''',
		f"{app}/{app}/__init__.py": "",
		f"{app}/public/js/extension.js": f"""// {title}: entry point loaded by BuildSuite Core.
// `sdk` is the stable surface (sdk.version); use sdk.vue instead of importing Vue.
export default function register(sdk) {{
	const {{ h }} = sdk.vue;

	// A banner above every Home page.
	sdk.slots.add("page.app-home.top", {{
		name: "{app}Banner",
		setup() {{
			return () => h("div", {{ class: "mb-3 px-3 py-2 text-xs border border-ink-200" }}, "Hello from {title}");
		}},
	}});
}}
""",
	}


def create_extension_app(app: str, title: str | None = None, dest: str | None = None) -> Path:
	"""Write the app skeleton under `dest` (default: the bench apps folder) and return its path."""
	if not _NAME.match(app or ""):
		frappe.throw(f"App name must be lowercase letters, digits and underscores: {app!r}")
	title = title or app.replace("_", " ").title()
	root = Path(dest or frappe.get_app_path("buildsuite_core", "..", "..")).resolve() / app
	if root.exists():
		frappe.throw(f"{root} already exists")
	for rel, body in _files(app, title, "Your Name", "you@example.com").items():
		path = root / rel
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(body)
	return root
