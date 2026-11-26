# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Team-scoped workflow notifications.

Two switches:
- Workflow.custom_team_scoped_notifications (on the Workflow form): which workflows use this. Their
  own Frappe email alert is switched off when ticked (workflow_validate), so nobody is told twice.
- Persona.team_scoped_notifications: whose notifications follow the project team.

When a document of a ticked workflow reaches a state marked "Send Email" (the workflow's own per-state
setting), the users who can act next (the next transitions' roles) are notified in-app (Notification
Log: the BuildSuite bell and Desk, emailed per each user's notification settings):
- when the document's project has a team: a user whose persona follows the project team (or who has
  no persona, unless they are a System Manager, who sees every project), only when they are on that
  team, whether or not they are on any other team;
- everyone else holding the role, as usual (a persona that does not follow the team overrides it);
- if that leaves nobody for the role (or the document has no project, or its project has no team),
  all its holders, so an approval is never missed.
Only users who can read the document, and never the user who just moved it.

Built on public Frappe mechanisms only (doc_events, the workflow's next-transition lookup,
Notification Log): nothing in Frappe/ERPNext is overridden. It reads only on a workflow state change,
through Frappe's document cache for the workflow and personas, so it needs no cache of its own."""

import frappe
from frappe import _

WORKFLOW_FLAG = "custom_team_scoped_notifications"
PERSONA_FLAG = "team_scoped_notifications"


def workflow_validate(doc, method=None):
	"""Workflow validate: a team-scoped workflow's notifications are sent by BuildSuite, so its own
	Frappe email alert (which goes to every holder of the role) is switched off."""
	if doc.get(WORKFLOW_FLAG) and doc.send_email_alert:
		doc.send_email_alert = 0


def _project_of(doc):
	"""The document's project: its own `project`, else the first line that names one (a Material
	Request carries the project on its lines)."""
	if doc.get("project"):
		return doc.project
	for row in doc.get("items") or []:
		if row.get("project"):
			return row.project
	return None


def _next_roles(doc, workflow, state):
	"""The roles that can act on the document in this state (the workflow's own lookup)."""
	try:
		from frappe.workflow.doctype.workflow_action.workflow_action import get_next_possible_transitions
	except ImportError:  # a Frappe without this helper: no team-scoped notifications
		return set()
	transitions = get_next_possible_transitions(workflow, state, doc) or []
	return {t.allowed for t in transitions if t.get("allowed")}


def _team_scoped_users(users):
	"""The users among `users` whose notifications follow the project team: their persona's switch is
	on, or they have no persona (and are not a System Manager, who sees every project)."""
	personas = frappe.get_all(
		"User", filters={"name": ["in", list(users)]}, fields=["name", "persona"], as_list=True
	)
	scoped = set()
	for user, persona in personas:
		if persona:
			if frappe.get_cached_value("Persona", persona, PERSONA_FLAG):
				scoped.add(user)
		elif "System Manager" not in frappe.get_roles(user):
			scoped.add(user)
	return scoped


def recipients(doc, roles):
	"""Who is told about the document's next step: see the module docstring."""
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
		holders = {u for u in get_users_with_role(role) if u not in ("Administrator", "Guest")}
		if not holders:
			continue
		scoped = _team_scoped_users(holders) if team else set()
		chosen = {u for u in holders if u not in scoped or u in team} or holders
		for user in chosen:
			if user != actor and frappe.has_permission(doc.doctype, "read", doc=doc, user=user):
				out.add(user)
	return out


def notify_on_workflow_change(doc, method=None):
	"""doc_events["*"]["on_change"]: for a team-scoped workflow, notify the next step's users when the
	document reaches a state marked "Send Email"."""
	from frappe.model.workflow import get_workflow_name

	workflow = get_workflow_name(doc.doctype)  # cached by Frappe; None for most document types
	if not workflow:
		return
	wf = frappe.get_cached_doc("Workflow", workflow)
	if not wf.get(WORKFLOW_FLAG):
		return
	state_field = wf.workflow_state_field or "workflow_state"
	if not doc.has_value_changed(state_field):
		return
	state = doc.get(state_field)
	if not any(s.state == state and s.send_email for s in wf.states):
		return

	roles = _next_roles(doc, workflow, state)
	users = recipients(doc, roles) if roles else set()
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
