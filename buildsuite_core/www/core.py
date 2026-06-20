import json
from pathlib import Path

import frappe
from frappe import _
from frappe.translate import get_messages_for_boot, get_translated_doctypes, get_user_lang
from frappe.utils import get_system_timezone
from frappe.utils.jinja_globals import is_rtl

from buildsuite_core.api.permission import has_app_permission

no_cache = 1


def get_context():
	if not has_app_permission():
		frappe.throw(_("You do not have permission to access BuildSuite Core"), frappe.PermissionError)

	context = frappe._dict()
	context.boot = get_boot()
	context.frontend_assets = get_frontend_assets()
	context.title = "BuildSuite Core"
	context.favicon = "/assets/buildsuite_core/images/bs-icon.svg"
	context.meta = {
		"title": "BuildSuite Core",
		"description": "Construction operations workspace for BuildSuite Core",
	}
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	if not has_app_permission():
		frappe.throw(_("You do not have permission to access BuildSuite Core"), frappe.PermissionError)
	return get_boot()


def get_boot():
	from buildsuite_core.hooks import APP_ROUTE

	csrf_token = getattr(frappe.session, "csrf_token", None)
	if not csrf_token:
		try:
			from frappe.sessions import get_csrf_token

			csrf_token = get_csrf_token()
		except Exception:
			csrf_token = ""

	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"session_user": frappe.session.user,
			"default_route": f"/{APP_ROUTE}",
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": csrf_token,
			"lang": get_user_lang(),
			"text_direction": "rtl" if is_rtl() else "ltr",
			"translated_doctypes": get_translated_doctypes(),
			"translated_messages": get_messages_for_boot(),
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
				or get_system_timezone(),
			},
		}
	)


def get_frontend_assets():
	manifest_path = Path(frappe.get_app_path("buildsuite_core", "public", "frontend", "manifest.json"))
	if not manifest_path.exists():
		return None

	manifest = json.loads(manifest_path.read_text())
	entry = manifest.get("index.html")
	if not entry:
		return None

	base_path = "/assets/buildsuite_core/frontend/"
	return frappe._dict(
		{
			"entry": f"{base_path}{entry['file']}",
			"styles": [f"{base_path}{css_file}" for css_file in entry.get("css", [])],
		}
	)
