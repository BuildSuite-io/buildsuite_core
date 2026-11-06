"""Apply Resend delivery events to Frappe's own Email Queue and Communication.

Mails leave through Resend's SMTP relay, so Resend only learns about a message once it is
accepted. These events (delivered, bounced, complained, ...) flow back through the webhook and are
written onto the Email Queue row the message came from, and onto its Communication's native
Delivery Status, so the usual Frappe views show the real outcome."""

import json

import frappe
from frappe.utils import add_days, get_datetime

# Resend event -> Communication.delivery_status. `sent` is the relay accepting the mail, which
# Frappe already records, so it changes nothing.
EVENT_STATUS = {
	"email.delivered": "Sent",
	"email.delivery_delayed": "Delayed",
	"email.opened": "Opened",
	"email.clicked": "Clicked",
	"email.bounced": "Bounced",
	"email.complained": "Marked As Spam",
	"email.failed": "Error",
	"email.suppressed": "Rejected",
}

# Later events must not be overwritten by earlier ones arriving out of order (a "delivered" that
# lands after a "bounced" must not hide the bounce). Higher wins.
_RANK = {
	s: i
	for i, s in enumerate(
		[
			"Sent",
			"Delayed",
			"Opened",
			"Clicked",
			"Soft-Bounced",
			"Error",
			"Rejected",
			"Bounced",
			"Marked As Spam",
		]
	)
}

MATCH_WINDOW_DAYS = 7


def event_status(event_type: str, data: dict) -> str | None:
	if event_type == "email.bounced" and (data.get("bounce") or {}).get("type") == "Transient":
		return "Soft-Bounced"
	return EVENT_STATUS.get(event_type)


def find_queue(account: str, data: dict) -> str | None:
	"""The Email Queue row a Resend event is about.

	First by Message-ID, which Frappe stores on the queue row and Resend echoes back. If Resend
	rewrote it, fall back to a mail from this account sent to the same recipient in the last week,
	preferring the one whose body mentions the subject."""
	message_id = (data.get("message_id") or "").strip("<> \t\n")
	if message_id and (name := frappe.db.get_value("Email Queue", {"message_id": message_id}, "name")):
		return name

	recipients = data.get("to") or []
	if not recipients:
		return None
	since = add_days(get_datetime(data.get("created_at") or frappe.utils.now_datetime()), -MATCH_WINDOW_DAYS)
	candidates = frappe.get_all(
		"Email Queue",
		filters={
			"email_account": account,
			"status": ["in", ["Sent", "Partially Sent"]],
			"modified": [">=", since],
			"name": ["in", _queues_for_recipients(recipients)],
		},
		pluck="name",
		order_by="modified desc",
		limit=10,
	)
	subject = (data.get("subject") or "").strip()
	if subject:
		for name in candidates:
			if subject in (frappe.db.get_value("Email Queue", name, "message") or ""):
				return name
	return candidates[0] if candidates else None


def _queues_for_recipients(recipients):
	return frappe.get_all(
		"Email Queue Recipient", filters={"recipient": ["in", recipients]}, pluck="parent", limit=200
	) or [""]


def apply_event(account: str, event_id: str, payload: dict) -> str:
	"""Record one event and update the mail it concerns. Returns the log outcome."""
	event_type = payload.get("type") or ""
	data = payload.get("data") or {}
	queue = find_queue(account, data)
	communication = frappe.db.get_value("Email Queue", queue, "communication") if queue else None

	outcome = "Unmatched"
	detail = None
	if queue:
		outcome = "No Change"
		status = event_status(event_type, data)
		bounce = data.get("bounce") or {}
		if bounce:
			detail = " | ".join(
				filter(None, [bounce.get("type"), bounce.get("subType"), bounce.get("message")])
			)
		updates = {"resend_email_id": data.get("email_id")}
		if status and _outranks(status, frappe.db.get_value("Email Queue", queue, "resend_status")):
			updates.update(resend_status=status, resend_detail=detail)
			outcome = "Applied"
			if communication:
				current = frappe.db.get_value("Communication", communication, "delivery_status")
				if _outranks(status, current):
					frappe.db.set_value("Communication", communication, "delivery_status", status)
					frappe.get_doc("Communication", communication).notify_update()
		frappe.db.set_value("Email Queue", queue, updates, update_modified=False)

	frappe.get_doc(
		{
			"doctype": "Resend Event Log",
			"event_id": event_id,
			"event_type": event_type,
			"outcome": outcome,
			"email_account": account,
			"resend_email_id": data.get("email_id"),
			"recipient": ", ".join(data.get("to") or [])[:140],
			"email_queue": queue,
			"communication": communication,
			"detail": detail,
			"payload": json.dumps(payload, indent=1),
		}
	).insert(ignore_permissions=True)
	return outcome


def _outranks(new: str, current: str | None) -> bool:
	# An unknown / empty current status (e.g. a plain "Sending" or None) is always replaced.
	return _RANK[new] > _RANK.get(current, -1)
