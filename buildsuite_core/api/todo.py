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


def _enrich_row(r, me, names):
	"""Shape a raw ToDo row (dict) for the SPA: plain-text description, ISO dates, assignee/author
	names, the referenced record's label, and the `read` flag. `names` is a user→full_name cache."""
	r["description"] = strip_html(r.get("description") or "").strip()
	r["date"] = str(r.date) if r.get("date") else None
	r["created_at"] = str(r.creation) if r.get("creation") else None
	r.pop("creation", None)
	r["allocated_to_name"] = names.get(r.allocated_to) or r.allocated_to
	r["assigned_by_name"] = names.get(r.assigned_by) or r.assigned_by
	r["reference_label"] = _ref_label(r.get("reference_type"), r.get("reference_name"))
	r["read"] = me in _seen_list(r.pop("_seen", None))
	return r


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
		_enrich_row(r, me, names)
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


def _visible_to_me(row, me):
	"""Same visibility as list_todos: mine, raised by me, or I'm a director/admin."""
	return _can_see_all() or me in (row.get("allocated_to"), row.get("assigned_by"), row.get("owner"))


# Fields whose Version-tracked changes are worth a timeline line, and the label to show for each.
# Anything not listed (internal / bookkeeping fields) is skipped.
_ACTIVITY_FIELDS = {
	"status": "status",
	"priority": "priority",
	"date": "due date",
	"description": "description",
	"allocated_to": "assignee",
}
# The icon key each change maps to on the frontend (WorkspaceIcon slugs, mirrors the prototype).
_FIELD_ACTION = {
	"status": "status",
	"priority": "status",
	"date": "due",
	"description": "edited",
	"allocated_to": "assigned",
}


def _describe_change(field, old, new, uname):
	"""A human sentence for one Version field change, or None to skip it."""
	label = _ACTIVITY_FIELDS.get(field)
	if not label:
		return None
	if field == "description":
		return "edited the description"
	if field == "allocated_to":
		return f"reassigned it to {uname(new)}" if new else "removed the assignee"
	old_txt = old if old not in (None, "") else "—"
	new_txt = new if new not in (None, "") else "—"
	if field == "date":
		old_txt, new_txt = (old or "no due date"), (new or "no due date")
	return f"changed {label} from “{old_txt}” to “{new_txt}”"


def get_todo_activity(name):
	"""The to-do's Frappe activity timeline, oldest first: its creation, every tracked field change
	(from Version — ToDo has track_changes on), and any comments left on it. Each entry is
	{id, action, by, by_name, at, text, is_comment}."""
	name_cache = {}

	def uname(user):
		if not user:
			return user
		if user not in name_cache:
			name_cache[user] = frappe.db.get_value("User", user, "full_name") or user
		return name_cache[user]

	meta = frappe.db.get_value(DOCTYPE, name, ["owner", "creation"], as_dict=True) or {}
	acts = [
		{
			"id": f"created-{name}",
			"action": "created",
			"by": meta.get("owner"),
			"by_name": uname(meta.get("owner")),
			"at": str(meta.get("creation")) if meta.get("creation") else None,
			"text": "raised this to-do",
			"is_comment": False,
		}
	]

	# Field changes — ToDo.track_changes is on, so Version rows carry the edit history.
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": DOCTYPE, "docname": name},
		fields=["name", "owner", "creation", "data"],
		order_by="creation asc",
		limit_page_length=0,
	)
	for v in versions:
		try:
			data = json.loads(v.data or "{}")
		except (ValueError, TypeError):
			continue
		for change in data.get("changed", []):
			field = change[0] if change else None
			old = change[1] if len(change) > 1 else None
			new = change[2] if len(change) > 2 else None
			text = _describe_change(field, old, new, uname)
			if not text:
				continue
			acts.append(
				{
					"id": f"{v.name}-{field}",
					"action": _FIELD_ACTION.get(field, "edited"),
					"by": v.owner,
					"by_name": uname(v.owner),
					"at": str(v.creation),
					"text": text,
					"is_comment": False,
				}
			)

	# Comments left on the to-do (user comments + Frappe's own info/activity comments).
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": DOCTYPE,
			"reference_name": name,
			"comment_type": ["in", ["Comment", "Info", "Edit", "Label", "Relinked", "Attachment"]],
		},
		fields=["name", "owner", "creation", "content", "comment_type", "comment_by"],
		order_by="creation asc",
		limit_page_length=0,
	)
	for c in comments:
		is_comment = c.comment_type == "Comment"
		acts.append(
			{
				"id": c.name,
				"action": "comment" if is_comment else "info",
				"by": c.owner,
				"by_name": uname(c.comment_by or c.owner),
				"at": str(c.creation),
				"text": strip_html(c.content or "").strip(),
				"is_comment": is_comment,
			}
		)

	acts.sort(key=lambda a: a.get("at") or "")
	return acts


@frappe.whitelist()
def get_todo(name):
	"""One to-do — enriched exactly like a list row — plus its Frappe activity timeline. Marks it
	read (its `_seen`). A to-do you may not see is reported as not-found, not forbidden, so the
	response never confirms that a to-do you can't read exists."""
	me = frappe.session.user
	fields = [
		"name", "description", "status", "priority", "date", "color",
		"allocated_to", "assigned_by", "reference_type", "reference_name", "creation", "_seen", "owner",
	]
	row = frappe.db.get_value(DOCTYPE, name, fields, as_dict=True) if frappe.db.exists(DOCTYPE, name) else None
	if not row or not _visible_to_me(row, me):
		frappe.throw(_("This to-do no longer exists, or it belongs to someone else."), frappe.DoesNotExistError)

	activity = get_todo_activity(name)
	_mark_read(name)

	names = {}
	for u in {row.get("allocated_to"), row.get("assigned_by")} - {None}:
		names[u] = frappe.db.get_value("User", u, "full_name") or u
	row.pop("owner", None)
	_enrich_row(row, me, names)
	return {"todo": row, "activity": activity}


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
