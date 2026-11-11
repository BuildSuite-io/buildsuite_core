# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe

from buildsuite_core.sdk import get_settings_pages


@frappe.whitelist()
def list_settings_pages() -> list[dict]:
	"""Settings pages that installed apps declare (buildsuite_settings_pages hook), for the SPA's
	Settings page. Only Single DocTypes the user can read."""
	return get_settings_pages()
