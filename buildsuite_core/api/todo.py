# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""To-dos — a thin wrapper over Frappe's standard ToDo doctype, surfaced in the SPA (top-nav badge
+ a list/board view). A to-do is visible to you when it's allocated to you or you raised it;
director / admin roles see everyone's. Frappe's own ToDo row permissions still apply.

One deliberate extension mirrors the prototype: an 'In Progress' status (a Select option added via
a property setter), so the board is three columns — Open → In Progress → Closed — not two."""

import json

import frappe
from frappe import _
from frappe.utils import strip_html

DOCTYPE = "ToDo"
_STATUSES = ("Open", "In Progress", "Closed", "Cancelled")
_STATUS_OPTIONS = "Open\nIn Progress\nClosed\nCancelled"
_PRIORITIES = ("High", "Medium", "Low")
# Roles that see every to-do (mirrors the prototype's TODO_ADMIN_ROLES: director/admin/bsa).
_CAN_SEE_ALL = {"System Manager", "BuildSuite Administrator", "BuildSuite Director"}
# reference_type -> the field to show as the record's label (fallback: its name).
_REF_TITLE = {
	"Project": "project_name",
	"Task": "subject",
	"Work Package": "package_name",
	"Stage Planning": "stage_name",
	"BOQ": "title",
	"Scope Change Order": "title",
	"Customer": "customer_name",
	"Supplier": "supplier_name",
}


def ensure_todo_status_option():
	"""Add 'In Progress' to ToDo.status (a property setter — the standard Frappe way to extend a
	Select). Idempotent; run on install + migrate so the board's third column is valid to save."""
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	frappe.make_property_setter(
		{
			"doctype": DOCTYPE,
			"fieldname": "status",
			"property": "options",
			"value": _STATUS_OPTIONS,
			"property_type": "Text",
		},
		is_system_generated=True,
	)


def _can_see_all():
	return bool(_CAN_SEE_ALL & set(frappe.get_roles()))


def _seen_list(raw):
	try:
		val = json.loads(raw or "[]")
		return val if isinstance(val, list) else []
	except (ValueError, TypeError):
		return []


def _mark_read(name, user=None):
	"""Add a user to the ToDo's Frappe `_seen` read-receipt (idempotent, no modified bump)."""
	user = user or frappe.session.user
	seen = _seen_list(frappe.db.get_value(DOCTYPE, name, "_seen"))
	if user not in seen:
		seen.append(user)
		frappe.db.set_value(DOCTYPE, name, "_seen", json.dumps(seen), update_modified=False)


def _ref_label(ref_type, ref_name):
	if not (ref_type and ref_name) or not frappe.db.exists("DocType", ref_type):
		return ref_name
	field = _REF_TITLE.get(ref_type)
	if field:
		return frappe.db.get_value(ref_type, ref_name, field) or ref_name
	return ref_name


@frappe.whitelist()
def list_todos():
	"""The current user's visible to-dos (all, for a director/admin; else allocated to or raised by
	me), each enriched with the assignee/author names and the referenced record's label. Returns
	{me, can_see_all, todos}. Descriptions come back as plain text."""
	me = frappe.session.user
	can_all = _can_see_all()
	fields = [
		"name", "description", "status", "priority", "date", "color",
		"allocated_to", "assigned_by", "reference_type", "reference_name", "creation", "_seen",
	]
	if can_all:
		rows = frappe.get_all(DOCTYPE, fields=fields, order_by="modified desc", limit_page_length=0)
	else:
		rows = frappe.get_all(
			DOCTYPE,
			or_filters={"allocated_to": me, "assigned_by": me, "owner": me},
			fields=fields,
			order_by="modified desc",
			limit_page_length=0,
		)

	users = {u for r in rows for u in (r.allocated_to, r.assigned_by) if u}
	names = (
		{u.name: (u.full_name or u.name) for u in frappe.get_all("User", filters={"name": ["in", list(users)]}, fields=["name", "full_name"])}
		if users
		else {}
	)
	for r in rows:
		r["description"] = strip_html(r.get("description") or "").strip()
		r["date"] = str(r.date) if r.get("date") else None
		r["created_at"] = str(r.creation) if r.get("creation") else None
		r.pop("creation", None)
		r["allocated_to_name"] = names.get(r.allocated_to) or r.allocated_to
		r["assigned_by_name"] = names.get(r.assigned_by) or r.assigned_by
		r["reference_label"] = _ref_label(r.get("reference_type"), r.get("reference_name"))
		# Frappe read-receipt: have I seen this to-do? (the `read` dot + unread badge)
		r["read"] = me in _seen_list(r.pop("_seen", None))
	return {"me": me, "can_see_all": can_all, "todos": rows}


@frappe.whitelist()
def my_unread_todo_count():
	"""The top-nav badge: to-dos allocated to me that I haven't opened yet (Frappe `_seen`).
	Cancelled ones don't count. My own to-dos are marked read on creation, so this is really
	'things other people put on my plate that I haven't looked at'."""
	me = frappe.session.user
	rows = frappe.get_all(
		DOCTYPE,
		filters={"allocated_to": me, "status": ["!=", "Cancelled"]},
		fields=["_seen"],
		limit_page_length=0,
	)
	return sum(1 for r in rows if me not in _seen_list(r.get("_seen")))


@frappe.whitelist()
def mark_todo_read(name):
	"""Mark a to-do read for the current user (its Frappe `_seen`) — called when it's opened."""
	_mark_read(name)
	return {"name": name, "read": True}


@frappe.whitelist()
def save_todo(name=None, description=None, priority="Medium", date=None, status=None, allocated_to=None):
	"""Create a to-do (raised by me, allocated to me unless someone else is picked) or update one."""
	description = (description or "").strip()
	if not description:
		frappe.throw(_("A to-do needs a description."))
	priority = priority if priority in _PRIORITIES else "Medium"
	if name:
		doc = frappe.get_doc(DOCTYPE, name)
		doc.description = description
		doc.priority = priority
		doc.date = date or None
		if status in _STATUSES:
			doc.status = status
		if allocated_to:
			doc.allocated_to = allocated_to
		doc.save()
	else:
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"description": description,
				"priority": priority,
				"date": date or None,
				"status": status if status in _STATUSES else "Open",
				"allocated_to": allocated_to or frappe.session.user,
				"assigned_by": frappe.session.user,
			}
		)
		doc.insert()
		# A to-do I raise is already "read" by me — only ones others assign me start unread.
		_mark_read(doc.name)
	return {"name": doc.name}


@frappe.whitelist()
def set_todo_status(name, status):
	"""Move a to-do to Open / In Progress / Closed / Cancelled (the board's one-tap advance + menu)."""
	if status not in _STATUSES:
		frappe.throw(_("Invalid status: {0}").format(status))
	doc = frappe.get_doc(DOCTYPE, name)
	doc.status = status
	doc.save()
	return {"name": doc.name, "status": status}


@frappe.whitelist()
def delete_todo(name):
	"""Delete a to-do."""
	frappe.delete_doc(DOCTYPE, name)
	return {"ok": True}
