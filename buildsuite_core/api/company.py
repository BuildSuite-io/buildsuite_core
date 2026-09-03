# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Company scope for the SPA. Single-company for now — see the single-company seam."""

import frappe
from frappe import _

from buildsuite_core.utils.project import default_company

# Org-wide branding is an administrator concern (mirrors api.core_settings.ADMIN_ROLES).
ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage company branding."), frappe.PermissionError)


@frappe.whitelist()
def active_company():
	"""The company finance transactions (and their pickers) are scoped to right now.

	Same resolver the server-side company guards use, so the frontend picker filters agree
	with them. `window.sysdefaults.company` is not reliably present (e.g. the standalone Vite
	dev server), so the SPA fetches this instead. Multi-company later: derive from context.
	"""
	return default_company()


@frappe.whitelist()
def company_branding() -> dict:
	"""The default company's branding — logo + letter-head subtext — for the Settings page
	and for confirming what the shared Letter Head is built from."""
	company = default_company()
	if not company:
		return {}
	meta = frappe.get_meta("Company")
	return {
		"company": company,
		"company_name": frappe.db.get_value("Company", company, "company_name") or company,
		"logo": frappe.db.get_value("Company", company, "custom_company_logo")
		if meta.has_field("custom_company_logo")
		else None,
		"letter_head_subtext": frappe.db.get_value("Company", company, "custom_letter_head_subtext")
		if meta.has_field("custom_letter_head_subtext")
		else None,
		"letter_head": "BuildSuite Standard",
	}


@frappe.whitelist()
def update_company_branding(
	logo: str | None = None, letter_head_subtext: str | None = None
) -> dict:
	"""Set the default company's logo / letter-head subtext (administrator only). Saving the
	Company fires Company.on_update → rebuild_letter_head, so every print format immediately
	reflects the new branding. Pass a field to change it; omit it to leave it unchanged
	(an empty string clears it)."""
	_require_admin()
	company = default_company()
	if not company:
		frappe.throw(_("No default company is configured."))

	doc = frappe.get_doc("Company", company)
	if logo is not None:
		doc.custom_company_logo = logo or None
	if letter_head_subtext is not None:
		doc.custom_letter_head_subtext = letter_head_subtext or None
	doc.save(ignore_permissions=True)
	return company_branding()


@frappe.whitelist()
def list_companies() -> list:
	"""All companies for the SPA list + topbar switcher, mapped to the store's shape. The SPA
	derives shortName/colour from these; `is_default` marks the resolved working company."""
	rows = frappe.get_all(
		"Company",
		fields=["name", "company_name", "abbr", "custom_company_logo"],
		order_by="company_name asc",
	)
	default = default_company()
	return [
		{
			"id": r.name,
			"name": r.company_name or r.name,
			"abbr": r.abbr or "",
			"logo": r.get("custom_company_logo") or "",
			"is_default": r.name == default,
			"project_count": frappe.db.count("Project", {"company": r.name}),
		}
		for r in rows
	]


@frappe.whitelist()
def set_active_company(company: str) -> str:
	"""Set the working company for the session (the topbar switcher). Persists it as the user's
	default Company so the server-side `default_company()` resolver — and every company-scoped
	guard/picker — follows the switcher. Read permission on the company is required."""
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} does not exist.").format(company))
	if not frappe.has_permission("Company", ptype="read", doc=company):
		frappe.throw(
			_("You do not have access to company {0}.").format(company), frappe.PermissionError
		)
	frappe.defaults.set_user_default("Company", company)
	return company
