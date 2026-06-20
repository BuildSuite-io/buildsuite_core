"""Rename the BuildSuite frontend website route in one shot.

The route appears in three coupled places:
  1. backend  — buildsuite_core/hooks.py            (`APP_ROUTE` constant)
  2. backend  — buildsuite_core/www/<route>.{py,html} (the SPA page; filename = route)
  3. frontend — frontend/src/utils/appRoute.js        (`APP_ROUTE_NAME` constant)

`rename_app_route(new_route)` rewrites the two constants and renames the www page,
so a single call keeps everything consistent. Paths are derived from this file's
location so it works with no site context (the `bench change-app-route` command)
or via `bench execute buildsuite_core.route.rename_app_route --kwargs "{...}"`.
"""

import os
import re

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))  # .../buildsuite_core/buildsuite_core
_APP_ROOT = os.path.dirname(_PKG_DIR)  # .../buildsuite_core
_HOOKS = os.path.join(_PKG_DIR, "hooks.py")
_WWW = os.path.join(_PKG_DIR, "www")
_APP_ROUTE_JS = os.path.join(_APP_ROOT, "frontend", "src", "utils", "appRoute.js")

_ROUTE_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_HOOKS_RE = re.compile(r'^(APP_ROUTE\s*=\s*")([^"]+)(")', re.MULTILINE)
_JS_RE = re.compile(r"^(export const APP_ROUTE_NAME = ')([^']+)(')", re.MULTILINE)


def current_route():
	"""Read the current route token from hooks.py (the source of truth)."""
	text = _read(_HOOKS)
	m = _HOOKS_RE.search(text)
	if not m:
		raise RuntimeError('Could not find `APP_ROUTE = "..."` in hooks.py')
	return m.group(2)


def rename_app_route(new_route):
	new_route = (new_route or "").strip().strip("/").lower()
	if not _ROUTE_RE.match(new_route):
		raise ValueError(
			f"Invalid route '{new_route}'. Use lowercase letters, digits and dashes, "
			"starting with a letter (e.g. 'core')."
		)

	old_route = current_route()
	if old_route == new_route:
		return f"Route is already '/{new_route}' — nothing to change."

	# 1) hooks.py constant
	_sub_in_file(_HOOKS, _HOOKS_RE, new_route)

	# 2) rename the www page (filename == route)
	renamed = []
	for ext in ("py", "html"):
		src = os.path.join(_WWW, f"{old_route}.{ext}")
		dst = os.path.join(_WWW, f"{new_route}.{ext}")
		if not os.path.exists(src):
			raise FileNotFoundError(f"Expected www page not found: {src}")
		if os.path.exists(dst):
			raise FileExistsError(f"Target already exists: {dst}")
		os.rename(src, dst)
		renamed.append(f"  www/{old_route}.{ext} -> www/{new_route}.{ext}")
	# drop the stale bytecode for the old module so imports resolve cleanly
	_purge_pyc(old_route)

	# 3) frontend constant
	if os.path.exists(_APP_ROUTE_JS):
		_sub_in_file(_APP_ROUTE_JS, _JS_RE, new_route)
		js_line = f"  frontend/src/utils/appRoute.js -> APP_ROUTE_NAME = '{new_route}'"
	else:
		js_line = "  (frontend/src/utils/appRoute.js not found — update APP_ROUTE_NAME manually)"

	return "\n".join(
		[
			f"Renamed app route '/{old_route}' -> '/{new_route}':",
			f'  hooks.py -> APP_ROUTE = "{new_route}"',
			*renamed,
			js_line,
			"",
			"Next steps:",
			"  1. cd frontend && npm run build      # rebuild the SPA with the new router base",
			"  2. bench --site <site> clear-cache   # reload website routes",
			"  3. restart bench (Ctrl-C + `bench start`)  so hooks + the renamed www page reload",
			f"  App now serves at /{new_route}",
		]
	)


# --- helpers -----------------------------------------------------------------


def _read(path):
	with open(path, encoding="utf-8") as fh:
		return fh.read()


def _sub_in_file(path, pattern, new_value):
	text = _read(path)
	new_text, n = pattern.subn(lambda m: f"{m.group(1)}{new_value}{m.group(3)}", text)
	if not n:
		raise RuntimeError(f"Could not find the route token to rewrite in {path}")
	with open(path, "w", encoding="utf-8") as fh:
		fh.write(new_text)


def _purge_pyc(route):
	cache = os.path.join(_WWW, "__pycache__")
	if not os.path.isdir(cache):
		return
	for fn in os.listdir(cache):
		if fn.startswith(f"{route}.") and fn.endswith(".pyc"):
			try:
				os.remove(os.path.join(cache, fn))
			except OSError:
				pass
