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

from buildsuite_core.permissions.setup import PERSONA_TO_ROLE

PERSONA_OPTIONS = list(PERSONA_TO_ROLE)
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
		fields=["name", "full_name", "email", "enabled", "persona"],
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
	# Company is optional. It isn't shown in the Vue user form, but when one can be
	# inferred we stamp it (best-effort) since it feeds project company inference —
	# new projects inherit the creator's company. Left blank when none is available.
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


@frappe.whitelist()
def delete_buildsuite_user(email):
	_require_admin()
	if email in SYSTEM_ACCOUNTS:
		frappe.throw(_("This account can't be deleted."))
	if email == frappe.session.user:
		frappe.throw(_("You can't delete your own account."))
	if not frappe.db.exists("User", email):
		frappe.throw(_("User not found."))
	frappe.delete_doc("User", email)
	return {"ok": True}


@frappe.whitelist()
def outgoing_email_configured():
	_require_admin()
	return bool(frappe.db.exists("Email Account", {"default_outgoing": 1, "awaiting_password": 0}))
