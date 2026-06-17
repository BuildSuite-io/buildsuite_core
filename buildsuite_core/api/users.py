# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""BuildSuite user administration — real Frappe User CRUD from the Vue app.

People are Frappe Users. A user's "persona" is the `persona` Select custom field
on User; the buildsuite_core.utils.user.sync_persona_roles validate hook keeps
exactly one BuildSuite role in sync with it. So we only ever set `persona` here —
never touch roles directly.
"""

import frappe
from frappe import _
from frappe.utils import cint

# Persona labels = the options on the User.persona Select field (and the role
# names in the frontend roles.js). Source of truth for role mapping is the hook.
PERSONA_OPTIONS = [
	"Director / Owner",
	"Project Manager",
	"Estimator",
	"Quantity Surveyor",
	"Site Engineer",
	"Foreman / Supervisor",
	"Procurement Officer",
	"Store Keeper",
	"Accountant",
	"HR Manager",
	"System Manager (Admin)",
	"BuildSuite Administrator",
]
ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}
SYSTEM_ACCOUNTS = ["Administrator", "Guest"]


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage users."), frappe.PermissionError)


def _validate_persona(persona):
	if persona not in PERSONA_OPTIONS:
		frappe.throw(_("Invalid persona."))


@frappe.whitelist()
def list_buildsuite_users():
	"""Enabled + disabled Users that carry a BuildSuite persona (excludes system accounts)."""
	_require_admin()
	return frappe.get_all(
		"User",
		filters={"persona": ["in", PERSONA_OPTIONS], "name": ["not in", SYSTEM_ACCOUNTS]},
		fields=["name", "full_name", "email", "enabled", "persona", "last_login"],
		order_by="full_name asc",
	)


@frappe.whitelist()
def create_buildsuite_user(full_name, email, persona, enabled=1, send_welcome=1):
	_require_admin()
	full_name = (full_name or "").strip()
	email = (email or "").strip().lower()
	if not full_name:
		frappe.throw(_("Full name is required."))
	if not email:
		frappe.throw(_("Email is required."))
	_validate_persona(persona)
	if frappe.db.exists("User", email):
		frappe.throw(_("A user with that email already exists."))

	parts = full_name.split(" ", 1)
	doc = frappe.new_doc("User")
	doc.email = email
	doc.first_name = parts[0]
	if len(parts) > 1:
		doc.last_name = parts[1]
	doc.enabled = 1 if cint(enabled) else 0
	doc.user_type = "System User"
	doc.persona = persona  # the validate hook assigns the matching BuildSuite role
	# Company isn't shown in the Vue user form — inherit the creator's company so
	# the persona's mandatory-company rule is satisfied. Fall back to the site
	# default (e.g. when the creator is Administrator with no company set).
	doc.company = (
		frappe.db.get_value("User", frappe.session.user, "company")
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)
	doc.send_welcome_email = 1 if cint(send_welcome) else 0
	doc.flags.ignore_permissions = True
	doc.insert()
	return {
		"name": doc.name,
		"email": doc.email,
		"full_name": doc.full_name,
		"enabled": doc.enabled,
		"persona": doc.persona,
	}


@frappe.whitelist()
def update_buildsuite_user(email, full_name=None, persona=None, enabled=None):
	_require_admin()
	if not frappe.db.exists("User", email):
		frappe.throw(_("User not found."))
	doc = frappe.get_doc("User", email)
	if full_name is not None:
		parts = (full_name or "").strip().split(" ", 1)
		doc.first_name = parts[0] if parts and parts[0] else doc.first_name
		doc.last_name = parts[1] if len(parts) > 1 else ""
	if persona is not None:
		_validate_persona(persona)
		doc.persona = persona
	if enabled is not None:
		doc.enabled = 1 if cint(enabled) else 0
	doc.flags.ignore_permissions = True
	doc.save()
	return {
		"name": email,
		"full_name": doc.full_name,
		"enabled": doc.enabled,
		"persona": doc.persona,
	}


@frappe.whitelist()
def send_user_welcome(email):
	_require_admin()
	frappe.get_doc("User", email).send_welcome_mail_to_user()
	return {"ok": True}


@frappe.whitelist()
def send_user_password_reset(email):
	_require_admin()
	from frappe.core.doctype.user.user import reset_password

	# SMTP-safe: reset_password swallows OutgoingEmailError and skips disabled /
	# Administrator accounts.
	reset_password(email)
	return {"ok": True}
