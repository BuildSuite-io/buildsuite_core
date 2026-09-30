# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Whitelisted helpers to manage a Project's team (the custom_team_members child
table — DocType "Project Team"). The Vue Team tab calls these; child-table edits
go through doc.append/save rather than frappe.client.set_value (which can't
reliably write Table fields). doc.check_permission("write") enforces the same
record-level project access as the rest of the app.
"""

import frappe
from frappe import _

from buildsuite_core.api.notification import emit

# Who is notified when a project's team changes. The Administrator always gets both the add and the
# remove — a fixed watcher, so the notification feature is exercised by any team edit.
_MEMBERSHIP_WATCHER = "Administrator"


def _team(doc):
	return [{"user": r.user, "full_name": r.full_name} for r in (doc.custom_team_members or [])]


def _notify_membership(project_doc, user, *, added, full_name=None):
	"""Raise an in-app notification for the watcher when a member joins or leaves a project."""
	member = full_name or frappe.db.get_value("User", user, "full_name") or user
	project_label = project_doc.get("project_name") or project_doc.name
	emit(
		for_user=_MEMBERSHIP_WATCHER,
		subject=(
			_("{0} was added to project {1}").format(member, project_label)
			if added
			else _("{0} was removed from project {1}").format(member, project_label)
		),
		# Access granted reads as a Share; access removed is a plain Alert.
		type="Share" if added else "Alert",
		document_type="Project",
		document_name=project_doc.name,
	)


@frappe.whitelist()
def get_project_team(project: str):
	doc = frappe.get_doc("Project", project)
	doc.check_permission("read")
	return _team(doc)


@frappe.whitelist()
def add_project_team_member(project: str, user: str):
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")

	if not frappe.db.exists("User", user):
		frappe.throw(_("Unknown user."))

	if any(row.user == user for row in (doc.custom_team_members or [])):
		return _team(doc)  # already a member — no-op

	doc.append("custom_team_members", {"user": user})
	doc.save()  # full_name is fetched from User on save
	_notify_membership(doc, user, added=True)
	return _team(doc)


@frappe.whitelist()
def remove_project_team_member(project: str, user: str):
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")

	removed = next((row for row in (doc.custom_team_members or []) if row.user == user), None)
	kept = [row for row in (doc.custom_team_members or []) if row.user != user]
	if len(kept) == len(doc.custom_team_members or []):
		return _team(doc)  # wasn't a member — no-op

	doc.custom_team_members = kept
	doc.save()
	_notify_membership(doc, user, added=False, full_name=removed.full_name if removed else None)
	return _team(doc)
