# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The user's personal to-do list — a thin wrapper over Frappe's standard ToDo doctype, surfaced
in the SPA top nav. A to-do is 'mine' when it's allocated to me or I created it; the badge counts
the ones still open and allocated to me. Frappe's own ToDo permissions still apply per row."""

import frappe
from frappe import _
from frappe.utils import strip_html

DOCTYPE = "ToDo"
_STATUSES = ("Open", "Closed", "Cancelled")
_PRIORITIES = ("High", "Medium", "Low")


@frappe.whitelist()
def list_my_todos():
	"""The current user's to-dos (assigned to them or created by them), Open first then by due
	date. Cancelled ones are hidden. Description is returned as plain text."""
	me = frappe.session.user
	rows = frappe.get_all(
		DOCTYPE,
		filters={"status": ["!=", "Cancelled"]},
		or_filters={"allocated_to": me, "owner": me},
		fields=[
			"name", "description", "status", "priority", "date",
			"reference_type", "reference_name", "allocated_to",
		],
		order_by="modified desc",
		limit_page_length=0,
	)
	for r in rows:
		r["description"] = strip_html(r.get("description") or "").strip()
	# Open first; within a group the earliest due date leads (undated last).
	rows.sort(key=lambda r: (r["status"] != "Open", str(r.get("date") or "9999-12-31")))
	return rows


@frappe.whitelist()
def my_open_todo_count():
	"""Count of the current user's OPEN to-dos allocated to them — the top-nav badge."""
	return frappe.db.count(DOCTYPE, {"status": "Open", "allocated_to": frappe.session.user})


@frappe.whitelist()
def save_todo(name=None, description=None, priority="Medium", date=None):
	"""Create a new to-do (allocated to me, Open) or update an existing one's text/priority/due."""
	description = (description or "").strip()
	if not description:
		frappe.throw(_("A to-do needs a description."))
	priority = priority if priority in _PRIORITIES else "Medium"
	if name:
		doc = frappe.get_doc(DOCTYPE, name)
		doc.description = description
		doc.priority = priority
		doc.date = date or None
		doc.save()
	else:
		doc = frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"description": description,
				"priority": priority,
				"date": date or None,
				"allocated_to": frappe.session.user,
				"status": "Open",
			}
		)
		doc.insert()
	return {"name": doc.name}


@frappe.whitelist()
def set_todo_status(name, status):
	"""Mark a to-do Open / Closed (done) / Cancelled."""
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
