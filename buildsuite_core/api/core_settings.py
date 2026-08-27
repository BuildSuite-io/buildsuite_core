# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted read/write for BuildSuite Core Settings (a Single doctype), so the
Vue Settings screen can persist org-wide settings server-side."""

import frappe
from frappe import _

from buildsuite_core.overrides.project import (
	NAME_SERIES_MODE,
	PROJECT_ID_MODE,
	default_project_series,
	project_naming_mode,
)

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SETTINGS = "BuildSuite Core Settings"
NAMING_MODES = [PROJECT_ID_MODE, NAME_SERIES_MODE]


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage settings."), frappe.PermissionError)


def _project_series_options():
	"""Every naming series configured on the Project doctype."""
	field = frappe.get_meta("Project").get_field("naming_series")
	if field and field.options:
		return [row.strip() for row in field.options.split("\n") if row.strip()]
	return []


def _petty_cash_options(company):
	"""Cash / Bank ledger accounts of the default company — the candidates the admin can choose
	as the petty-cash float that petty cash and expenses post to/from."""
	if not company:
		return []
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_type": ["in", ["Cash", "Bank"]]},
		fields=["name", "account_type"],
		order_by="account_type, name",
	)


@frappe.whitelist()
def get_core_settings():
	"""The org-wide settings for the admin Settings screen."""
	_require_admin()
	from buildsuite_core.utils.project import default_company

	settings = frappe.get_single(SETTINGS)
	company = default_company()
	return {
		"project_naming": project_naming_mode(),
		"project_naming_modes": NAMING_MODES,
		"petty_cash_account": settings.default_petty_cash_account,
		"petty_cash_options": _petty_cash_options(company),
	}


@frappe.whitelist()
def get_letter_head():
	"""The branding band every printed surface (docs + reports) renders. Resolves the
	default Letter Head, falling back to the seeded 'BuildSuite Standard'. Read-only and
	available to any authenticated user, so all print views share one source of truth."""
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_print_assets import (
		LETTER_HEAD,
	)

	name = (
		frappe.db.get_value("Letter Head", {"is_default": 1, "disabled": 0}, "name")
		or (LETTER_HEAD if frappe.db.exists("Letter Head", LETTER_HEAD) else None)
	)
	if not name:
		return None
	return {"name": name, "content": frappe.db.get_value("Letter Head", name, "content")}


@frappe.whitelist()
def set_petty_cash_account(account: str | None = None):
	"""Set the configurable Petty Cash Account — the Cash/Bank float petty cash and expenses
	post to/from. Must be a ledger Cash/Bank account of the default company."""
	_require_admin()
	from buildsuite_core.utils.project import default_company

	account = (account or "").strip() or None
	if account:
		acc = frappe.db.get_value("Account", account, ["is_group", "company", "account_type"], as_dict=True)
		if not acc or acc.is_group:
			frappe.throw(_("Choose a ledger (non-group) account."))
		company = default_company()
		if company and acc.company != company:
			frappe.throw(_("The petty cash account must belong to {0}.").format(company))
		if acc.account_type not in ("Cash", "Bank"):
			frappe.throw(_("The petty cash account must be a Cash or Bank account."))
	doc = frappe.get_single(SETTINGS)
	doc.default_petty_cash_account = account
	doc.flags.ignore_permissions = True
	doc.save()
	return {"petty_cash_account": doc.default_petty_cash_account}


@frappe.whitelist()
def set_project_naming(project_naming: str):
	"""Set the project naming MODE ('Project ID' | 'Name Series'). The specific series
	is chosen per-project on the New Project form, not here."""
	_require_admin()
	if project_naming not in NAMING_MODES:
		frappe.throw(_("Project naming must be one of {0}.").format(", ".join(NAMING_MODES)))
	doc = frappe.get_single(SETTINGS)
	doc.project_naming = project_naming
	doc.flags.ignore_permissions = True
	doc.save()
	return {"project_naming": project_naming}


@frappe.whitelist()
def get_project_naming():
	"""The naming mode + the series options the New Project form needs. Available to
	any signed-in user (anyone who can create a project), unlike the admin settings."""
	return {
		"project_naming": project_naming_mode(),
		"series_options": _project_series_options(),
		"default_series": default_project_series(),
	}
