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
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"default_route": "/buildsuite_core",
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
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
