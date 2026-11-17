"""Resend as an Email Account service.

Mail leaves through Resend's SMTP relay, so Notifications, workflow alerts and every other sender
that uses an Email Account work unchanged. `account` pins the account to the relay, `signature` +
`delivery` write Resend's delivery webhooks (bounces, complaints, ...) back onto the Email Queue and
Communication; the endpoint is api.resend.webhook."""

SERVICE = "Resend"
