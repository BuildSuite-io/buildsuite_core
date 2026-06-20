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


def _team(doc):
	return [{"user": r.user, "full_name": r.full_name} for r in (doc.custom_team_members or [])]


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
	return _team(doc)


@frappe.whitelist()
def remove_project_team_member(project: str, user: str):
	doc = frappe.get_doc("Project", project)
	doc.check_permission("write")

	kept = [row for row in (doc.custom_team_members or []) if row.user != user]
	if len(kept) == len(doc.custom_team_members or []):
		return _team(doc)  # wasn't a member — no-op

	doc.custom_team_members = kept
	doc.save()
	return _team(doc)
