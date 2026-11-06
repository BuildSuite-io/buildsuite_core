import frappe

from buildsuite_core.resend import SERVICE

SMTP_HOST = "smtp.resend.com"
# 2587 (STARTTLS) and 2465 (SSL) are Resend's alternates to 587/465, for networks that filter the
# standard SMTP ports. Resend serves the same relay on all of them.
DEFAULT_PORT = "2587"
SSL_PORTS = ("465", "2465")
SMTP_USER = "resend"  # Resend's SMTP username is literally "resend"; the password is the API key.


def apply_resend_defaults(doc, method=None):
	"""Pin a Resend account to Resend's SMTP relay.

	Runs before the controller's validate (which tests the SMTP connection), so the login and host
	are already right when that check happens. Mirrors what core does for Sendgrid."""
	if doc.service != SERVICE:
		return
	doc.enable_outgoing = 1
	doc.enable_incoming = 0
	doc.use_imap = 0
	doc.login_id_is_different = 1
	doc.login_id = SMTP_USER
	doc.smtp_server = SMTP_HOST
	doc.smtp_port = str(doc.smtp_port or DEFAULT_PORT)
	# The port decides the transport: implicit SSL on 465/2465, STARTTLS on the rest.
	doc.use_ssl_for_outgoing = 1 if doc.smtp_port in SSL_PORTS else 0
	doc.use_tls = 0 if doc.use_ssl_for_outgoing else 1
	doc.no_smtp_authentication = 0
	doc.always_use_account_email_id_as_sender = 1
