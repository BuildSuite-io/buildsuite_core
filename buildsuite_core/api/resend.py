# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Resend delivery-status webhook (see buildsuite_core.resend)."""

import json

import frappe
from frappe.utils.password import get_decrypted_password

from buildsuite_core.resend import SERVICE
from buildsuite_core.resend.delivery import apply_event
from buildsuite_core.resend.signature import InvalidSignature, verify


# Called by Resend, not a logged-in user, so it is guest-accessible; the signature is the auth.
@frappe.whitelist(allow_guest=True, methods=["POST"])  # nosemgrep
def webhook(account: str | None = None):
	"""Resend webhook for ONE Email Account: /api/method/buildsuite_core.api.resend.webhook?account=<name>.

	Each Resend account has its own signing secret, kept on its Email Account, so the account in the
	URL selects which secret verifies the call. Nothing is read or written until the signature
	checks out. Unmatched or duplicate events still answer 200 so Resend does not retry them."""
	body = frappe.request.get_data()
	if not account or frappe.db.get_value("Email Account", account, "service") != SERVICE:
		frappe.throw("Unknown Resend account", frappe.AuthenticationError)

	secret = get_decrypted_password("Email Account", account, "resend_webhook_secret", raise_exception=False)
	try:
		event_id = verify(secret, frappe.request.headers, body)
	except InvalidSignature as e:
		frappe.throw(f"Webhook verification failed: {e}", frappe.AuthenticationError)

	if frappe.db.exists("Resend Event Log", event_id):
		return {"outcome": "Duplicate"}
	return {"outcome": apply_event(account, event_id, json.loads(body))}
