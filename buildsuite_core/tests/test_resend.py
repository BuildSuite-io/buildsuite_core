# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Resend as an Email Account service: SMTP defaults, signed delivery webhook, status write-back."""

import base64
import hashlib
import hmac
import json
import time

import frappe
from frappe.utils.password import set_encrypted_password

from buildsuite_core.api import resend as api
from buildsuite_core.resend.delivery import apply_event, event_status
from buildsuite_core.resend.signature import InvalidSignature, verify
from buildsuite_core.tests.base import BuildSuiteTestCase

KEY = b"super-secret-key-bytes"
SECRET = "whsec_" + base64.b64encode(KEY).decode()


def sign(body: bytes, msg_id="msg_1", ts=None, key=KEY):
	ts = str(int(ts if ts is not None else time.time()))
	mac = hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()
	return {"svix-id": msg_id, "svix-timestamp": ts, "svix-signature": "v1," + base64.b64encode(mac).decode()}


class TestResendEmailAccount(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()

	def _account(self, email, **kw):
		# awaiting_password skips the live SMTP connection test, so this runs offline.
		return frappe.get_doc(
			{
				"doctype": "Email Account",
				"email_account_name": email.split("@")[0],
				"email_id": email,
				"service": "Resend",
				"awaiting_password": 1,
				**kw,
			}
		).insert(ignore_permissions=True)

	def test_resend_is_a_service_option(self):
		self.assertIn("Resend", frappe.get_meta("Email Account").get_field("service").options.split("\n"))

	def test_defaults_point_at_resend_smtp(self):
		acc = self._account("notify@resend-one.test")
		self.assertEqual(acc.smtp_server, "smtp.resend.com")
		self.assertEqual(acc.login_id, "resend")
		self.assertEqual(
			(acc.smtp_port, acc.use_tls, acc.enable_outgoing, acc.enable_incoming), ("2587", 1, 1, 0)
		)

	def test_several_resend_accounts_coexist(self):
		a = self._account("a@resend-a.test")
		b = self._account("b@resend-b.test")
		self.assertNotEqual(a.name, b.name)
		self.assertEqual({a.service, b.service}, {"Resend"})

	def test_ssl_port_switches_transport_to_ssl(self):
		acc = self._account("ssl@resend-ssl.test", smtp_port="2465")
		self.assertEqual((acc.smtp_port, acc.use_ssl_for_outgoing, acc.use_tls), ("2465", 1, 0))


class TestSignature(BuildSuiteTestCase):
	def test_valid_signature_returns_delivery_id(self):
		body = b'{"type":"email.delivered"}'
		self.assertEqual(verify(SECRET, sign(body), body), "msg_1")

	def test_rotation_accepts_any_listed_signature(self):
		body = b"{}"
		h = sign(body)
		h["svix-signature"] = "v1,AAAA " + h["svix-signature"]
		self.assertEqual(verify(SECRET, h, body), "msg_1")

	def test_rejects_tampered_body_wrong_secret_stale_and_missing(self):
		body = b'{"a":1}'
		with self.assertRaises(InvalidSignature):
			verify(SECRET, sign(body), b'{"a":2}')
		with self.assertRaises(InvalidSignature):
			verify(SECRET, sign(body, key=b"other"), body)
		with self.assertRaises(InvalidSignature):
			verify(SECRET, sign(body, ts=time.time() - 3600), body)
		with self.assertRaises(InvalidSignature):
			verify(SECRET, {}, body)
		with self.assertRaises(InvalidSignature):
			verify(None, sign(body), body)


class TestDelivery(BuildSuiteTestCase):
	def setUp(self):
		super().setUp()
		self.account = (
			frappe.get_doc(
				{
					"doctype": "Email Account",
					"email_account_name": "resend-hook",
					"email_id": "hook@resend-hook.test",
					"service": "Resend",
					"awaiting_password": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.comm = (
			frappe.get_doc(
				{
					"doctype": "Communication",
					"communication_type": "Communication",
					"communication_medium": "Email",
					"sent_or_received": "Sent",
					"subject": "Hello PO",
					"delivery_status": "Sent",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.queue = self._queue("mid-111@frappe.test", "buyer@example.test", self.comm)

	def _queue(self, message_id, recipient, communication=None):
		return (
			frappe.get_doc(
				{
					"doctype": "Email Queue",
					"sender": "hook@resend-hook.test",
					"message": "Subject: Hello PO\n\nbody",
					"message_id": message_id,
					"status": "Sent",
					"email_account": self.account,
					"communication": communication,
					"recipients": [{"recipient": recipient, "status": "Sent"}],
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _event(self, kind, **data):
		base = {
			"email_id": "re_1",
			"message_id": "<mid-111@frappe.test>",
			"to": ["buyer@example.test"],
			"subject": "Hello PO",
		}
		return {"type": kind, "data": {**base, **data}}

	def _state(self):
		return (
			frappe.db.get_value(
				"Email Queue", self.queue, ["resend_status", "resend_email_id", "resend_detail"], as_dict=True
			),
			frappe.db.get_value("Communication", self.comm, "delivery_status"),
		)

	def test_bounce_matched_by_message_id_updates_queue_and_communication(self):
		bounce = {"type": "Permanent", "subType": "Suppressed", "message": "mailbox unavailable"}
		self.assertEqual(
			apply_event(self.account, "e1", self._event("email.bounced", bounce=bounce)), "Applied"
		)
		q, comm = self._state()
		self.assertEqual((q.resend_status, q.resend_email_id, comm), ("Bounced", "re_1", "Bounced"))
		self.assertIn("mailbox unavailable", q.resend_detail)

	def test_transient_bounce_is_soft(self):
		self.assertEqual(event_status("email.bounced", {"bounce": {"type": "Transient"}}), "Soft-Bounced")
		self.assertEqual(event_status("email.complained", {}), "Marked As Spam")
		self.assertIsNone(event_status("email.sent", {}))

	def test_late_delivered_does_not_hide_a_bounce(self):
		apply_event(self.account, "e1", self._event("email.bounced", bounce={"type": "Permanent"}))
		self.assertEqual(apply_event(self.account, "e2", self._event("email.delivered")), "No Change")
		self.assertEqual(self._state()[1], "Bounced")

	def test_falls_back_to_recipient_when_message_id_was_rewritten(self):
		ev = self._event("email.complained", message_id="<rewritten@resend>")
		self.assertEqual(apply_event(self.account, "e3", ev), "Applied")
		self.assertEqual(self._state()[1], "Marked As Spam")

	def test_unmatched_event_is_logged_not_applied(self):
		ev = self._event("email.bounced", message_id="<nope@x>", to=["stranger@example.test"])
		self.assertEqual(apply_event(self.account, "e4", ev), "Unmatched")
		self.assertEqual(frappe.db.get_value("Resend Event Log", "e4", "outcome"), "Unmatched")
		self.assertEqual(self._state()[1], "Sent")

	def test_webhook_rejects_bad_signature_and_non_resend_account(self):
		frappe.set_user("Guest")
		try:
			frappe.local.request = frappe._dict(get_data=lambda: b"{}", headers={})
			with self.assertRaises(frappe.AuthenticationError):
				api.webhook(account=self.account)  # no secret / signature
			with self.assertRaises(frappe.AuthenticationError):
				api.webhook(account="Notifications")  # not a Resend account
		finally:
			frappe.set_user("Administrator")

	def test_webhook_end_to_end_and_duplicate(self):
		set_encrypted_password("Email Account", self.account, SECRET, "resend_webhook_secret")
		body = json.dumps(self._event("email.complained")).encode()
		frappe.local.request = frappe._dict(get_data=lambda: body, headers=sign(body, msg_id="msg_e2e"))
		self.assertEqual(api.webhook(account=self.account), {"outcome": "Applied"})
		self.assertEqual(api.webhook(account=self.account), {"outcome": "Duplicate"})
		self.assertEqual(self._state()[1], "Marked As Spam")
