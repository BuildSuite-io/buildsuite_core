# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted admin CRUD for the Persona master and its role mapping.

The Vue Settings → Personas screen edits personas here rather than through the
generic client adapter, because a persona's `roles` child table can't be written
reliably via frappe.client.set_value. Only an administrator (System Manager /
BuildSuite Administrator) may manage personas — the same gate as user admin.
"""

import frappe
from frappe import _
from frappe.utils import cint

ADMIN_ROLES = {"System Manager", "BuildSuite Administrator"}


def _require_admin():
	if not (set(frappe.get_roles()) & ADMIN_ROLES):
		frappe.throw(_("Only an administrator can manage personas."), frappe.PermissionError)


def _serialize(doc):
	return {
		"name": doc.name,
		"persona_name": doc.persona_name,
		"slug": doc.slug,
		"description": doc.description,
		"enabled": doc.enabled,
		"sort_order": doc.sort_order,
		"is_default": doc.is_default,
		"roles": [r.role for r in doc.roles],
	}


@frappe.whitelist()
def list_personas():
	"""All personas with their mapped roles, for the settings list."""
	_require_admin()
	rows = frappe.get_all(
		"Persona",
		fields=["name", "persona_name", "slug", "enabled", "sort_order"],
		order_by="sort_order asc",
	)
	for row in rows:
		row["roles"] = frappe.get_all("Persona Role", filters={"parent": row["name"]}, pluck="role")
	return rows


@frappe.whitelist()
def get_persona(name: str):
	"""One persona with its full role list."""
	_require_admin()
	if not frappe.db.exists("Persona", name):
		frappe.throw(_("Persona not found."))
	return _serialize(frappe.get_doc("Persona", name))


@frappe.whitelist()
def list_assignable_roles():
	"""Roles a persona may grant — the BuildSuite roles plus native System Manager.
	Excludes the workflow-editor marker, which the sync hook grants automatically."""
	_require_admin()
	from buildsuite_core.permissions.setup import WORKFLOW_EDITOR_ROLE

	roles = frappe.get_all("Role", filters={"name": ["like", "BuildSuite %"]}, pluck="name")
	if frappe.db.exists("Role", "System Manager"):
		roles.append("System Manager")
	return sorted(set(roles) - {WORKFLOW_EDITOR_ROLE})


@frappe.whitelist()
def save_persona(
	name=None,
	persona_name=None,
	slug=None,
	description=None,
	enabled=1,
	sort_order=0,
	roles=None,
):
	"""Create or update a persona. The persona_name is the record key and is only
	settable on create (renaming would orphan the User.persona links that point at
	it). Roles are replaced wholesale from the payload."""
	_require_admin()
	roles = frappe.parse_json(roles) or []

	if name and frappe.db.exists("Persona", name):
		doc = frappe.get_doc("Persona", name)
	else:
		doc = frappe.new_doc("Persona")
		doc.persona_name = (persona_name or "").strip()
		if not doc.persona_name:
			frappe.throw(_("Persona name is required."))
		if frappe.db.exists("Persona", doc.persona_name):
			frappe.throw(_("A persona with that name already exists."))

	if slug is not None:
		doc.slug = (slug or "").strip()
	if description is not None:
		doc.description = description
	doc.enabled = 1 if cint(enabled) else 0
	doc.sort_order = cint(sort_order)

	doc.set("roles", [])
	for role in roles:
		if frappe.db.exists("Role", role):
			doc.append("roles", {"role": role})

	doc.flags.ignore_permissions = True
	doc.save()
	return _serialize(doc)


@frappe.whitelist()
def delete_persona(name: str):
	"""Delete a persona once no user is assigned it."""
	_require_admin()
	if not frappe.db.exists("Persona", name):
		frappe.throw(_("Persona not found."))
	in_use = frappe.db.count("User", {"persona": name})
	if in_use:
		frappe.throw(
			_("{0} user(s) are still assigned this persona — reassign them first.").format(in_use)
		)
	frappe.delete_doc("Persona", name, ignore_permissions=True)
	return {"ok": True}
