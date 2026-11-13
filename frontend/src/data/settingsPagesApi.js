import { frappeRequest } from "frappe-ui-frappe-request";

// Settings pages that installed apps declare through the buildsuite_settings_pages hook:
// [{ doctype, group, label, description, icon }]. Each is a Single DocType, rendered by the
// generic form at /settings/doc/<doctype>.
export const listSettingsPages = () =>
	frappeRequest({ url: "buildsuite_core.api.settings_pages.list_settings_pages" });
