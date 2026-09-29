# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Notifications — a thin wrapper over Frappe's standard Notification Log doctype, surfaced in the
SPA (top-nav bell + dropdown, a generic list view, and a bespoke detail view). Each Notification Log
row belongs to one recipient (`for_user`) and carries its own `read` flag, so 'seen' is per-row —
simpler than the ToDo `_seen` list. Mirrors the prototype's notification feature 1:1.

Frappe already scopes Notification Log to the current user (its get_permission_query_conditions), and
ships mark_as_read / mark_all_as_read; these wrappers add the enrichment (sender name, reference
label, plain subject) the SPA needs and keep the read/count semantics beside the ToDo ones."""

import frappe
from frappe import _
from frappe.utils import strip_html

DOCTYPE = "Notification Log"
_FIELDS = [
	"name", "subject", "type", "document_type", "document_name",
	"from_user", "read", "creation", "link", "email_content",
]


def _doc_label(doctype, docname):
	"""The referenced record's human title (its title field), else its name."""
	if not (doctype and docname) or not frappe.db.exists("DocType", doctype):
		return docname
	if not frappe.db.exists(doctype, docname):
		return docname
	title_field = frappe.get_meta(doctype).get("title_field")
	if title_field:
		return frappe.db.get_value(doctype, docname, title_field) or docname
	return docname


def _enrich(rows):
	"""Shape Notification Log rows for the SPA: plain-text subject, sender name, ISO creation, a bool
	`read`, and the referenced record's label. `email_content` (the HTML body) is passed through."""
	senders = {r.get("from_user") for r in rows if r.get("from_user")}
	names = (
		{
			u.name: (u.full_name or u.name)
			for u in frappe.get_all("User", filters={"name": ["in", list(senders)]}, fields=["name", "full_name"])
		}
		if senders
		else {}
	)
	for r in rows:
		r["subject"] = strip_html(r.get("subject") or "").strip()
		r["from_user_name"] = names.get(r.get("from_user")) or r.get("from_user")
		r["creation"] = str(r.get("creation")) if r.get("creation") else None
		r["read"] = bool(r.get("read"))
		r["reference_label"] = _doc_label(r.get("document_type"), r.get("document_name"))
	return rows


@frappe.whitelist()
def list_notifications(limit=20):
	"""The current user's notifications (newest first), enriched — the bell dropdown. Returns
	{me, notifications}."""
	me = frappe.session.user
	rows = frappe.get_all(
		DOCTYPE,
		filters={"for_user": me},
		fields=_FIELDS,
		order_by="creation desc",
		limit_page_length=int(limit or 20),
	)
	return {"me": me, "notifications": _enrich(rows)}


@frappe.whitelist()
def my_unseen_count():
	"""Unread notifications for the current user — the top-nav bell badge (mirrors the to-do badge)."""
	return frappe.db.count(DOCTYPE, {"for_user": frappe.session.user, "read": 0})


@frappe.whitelist()
def get_notification(name):
	"""One notification — must belong to the current user — enriched, and marked read as a side
	effect. A notification that isn't yours is reported as not-found, so the response never confirms
	that someone else's notification exists."""
	me = frappe.session.user
	row = (
		frappe.db.get_value(DOCTYPE, name, [*_FIELDS, "for_user"], as_dict=True)
		if frappe.db.exists(DOCTYPE, name)
		else None
	)
	if not row or row.get("for_user") != me:
		frappe.throw(_("This notification no longer exists, or it isn't yours."), frappe.DoesNotExistError)
	if not row.get("read"):
		frappe.db.set_value(DOCTYPE, name, "read", 1, update_modified=False)
		row["read"] = 1
	row.pop("for_user", None)
	_enrich([row])
	return row


@frappe.whitelist()
def mark_notification_read(name):
	"""Mark one of my notifications read (its `read` flag)."""
	frappe.db.set_value(
		DOCTYPE, {"name": str(name), "for_user": frappe.session.user}, "read", 1, update_modified=False
	)
	return {"name": name, "read": True}


@frappe.whitelist()
def mark_all_notifications_read():
	"""Mark all of the current user's unread notifications read (the dropdown's 'Mark all as read')."""
	names = [
		d.name
		for d in frappe.get_all(DOCTYPE, filters={"for_user": frappe.session.user, "read": 0})
	]
	if names:
		frappe.db.set_value(DOCTYPE, {"name": ["in", names]}, "read", 1, update_modified=False)
	return {"count": len(names)}
