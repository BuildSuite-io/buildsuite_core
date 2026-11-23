# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Team-scoped workflow notifications.

For each document type listed under Project Settings > Team-scoped workflow notifications: when a
document's workflow state changes, the users who can act next are notified in-app (Notification Log,
so the BuildSuite bell and Desk, emailed per each user's own notification settings). Only those of
them on the document's project team are told; when nobody with that role is on the team (or the
document has no project), everyone with the role who can read the document is told, so an approval
is never left with nobody aware of it.

Built on public Frappe mechanisms only (a doc_events hook, the workflow's own next-transition lookup,
Notification Log): Frappe's workflow itself (states, transitions, Workflow Action, its optional
"Send Email Alert") is untouched. A document type not in the list is skipped at once."""

import frappe
from frappe import _

CACHE_KEY = "buildsuite_team_scoped_workflows"
SETTINGS = "Project Settings"


def team_scoped_doctypes():
	"""The document types listed in Project Settings (cached; cleared when the settings are saved)."""

	def load():
		if not frappe.db.exists("DocType", "Team Scoped Workflow"):
			return []
		return frappe.get_all(
			"Team Scoped Workflow",
			filters={"parenttype": SETTINGS, "parent": SETTINGS, "parentfield": "team_scoped_workflows"},
			pluck="document_type",
		)

	return frappe.cache.get_value(CACHE_KEY, generator=load) or []


def clear_cache():
	frappe.cache.delete_value(CACHE_KEY)


def _project_of(doc):
	"""The document's project: its own `project`, else the first line that names one (a Material
	Request carries the project on its lines)."""
	if doc.get("project"):
		return doc.project
	for row in doc.get("items") or []:
		if row.get("project"):
			return row.project
	return None


def _next_roles(doc, workflow):
	"""The roles that can act on the document in its new state (the workflow's own lookup)."""
	try:
		from frappe.workflow.doctype.workflow_action.workflow_action import (
			get_doc_workflow_state,
			get_next_possible_transitions,
		)
	except ImportError:  # an older / newer Frappe without these helpers: no team notifications
		return set(), None
	state = get_doc_workflow_state(doc)
	transitions = get_next_possible_transitions(workflow, state, doc) or []
	return {t.allowed for t in transitions if t.get("allowed")}, state


def recipients(doc, roles):
	"""Per role: its holders on the project's team, else all its holders; only users who can read
	the document, never the user who just moved it."""
	from frappe.utils.user import get_users_with_role

	project = _project_of(doc)
	team = (
		set(
			frappe.get_all("Project Team", filters={"parent": project, "parenttype": "Project"}, pluck="user")
		)
		if project
		else set()
	)
	actor = frappe.session.user
	out = set()
	for role in roles:
		holders = [u for u in get_users_with_role(role) if u not in ("Administrator", "Guest")]
		on_team = [u for u in holders if u in team]
		for user in on_team or holders:
			if user != actor and frappe.has_permission(doc.doctype, "read", doc=doc, user=user):
				out.add(user)
	return out


def notify_on_workflow_change(doc, method=None):
	"""doc_events["*"]["on_change"]: notify the project team when a listed document's workflow
	state changes."""
	if doc.doctype not in team_scoped_doctypes():
		return
	from frappe.model.workflow import get_workflow_name

	workflow = get_workflow_name(doc.doctype)
	if not workflow:
		return
	state_field = frappe.get_cached_value("Workflow", workflow, "workflow_state_field") or "workflow_state"
	if not doc.has_value_changed(state_field):
		return

	roles, state = _next_roles(doc, workflow)
	if not roles:
		return
	users = recipients(doc, roles)
	if not users:
		return

	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	enqueue_create_notification(
		list(users),
		{
			"type": "Alert",
			"document_type": doc.doctype,
			"document_name": doc.name,
			"subject": _("{0} {1} is {2} and waiting for you").format(_(doc.doctype), doc.name, _(state)),
			"from_user": frappe.session.user,
		},
	)
