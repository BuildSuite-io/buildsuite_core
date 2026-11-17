"""Verify a Resend (Svix / Standard Webhooks) signature without the svix package.

Signed content is `<id>.<timestamp>.<raw body>`, HMAC-SHA256 with the base64 key that follows the
`whsec_` prefix of the signing secret. The signature header holds space-separated `v1,<base64>`
entries (several during a secret rotation)."""

import base64
import hashlib
import hmac
import time

TOLERANCE_SECONDS = 300


class InvalidSignature(Exception):
	pass


def _header(headers, name):
	return headers.get(f"svix-{name}") or headers.get(f"webhook-{name}")


def verify(secret: str, headers, body: bytes, now: float | None = None) -> str:
	"""Return the delivery id (svix-id) when the signature is valid, else raise InvalidSignature."""
	msg_id, timestamp, signatures = (_header(headers, n) for n in ("id", "timestamp", "signature"))
	if not (secret and msg_id and timestamp and signatures):
		raise InvalidSignature("Missing signature headers")

	try:
		sent_at = int(timestamp)
	except ValueError:
		raise InvalidSignature("Bad timestamp") from None
	if abs((now if now is not None else time.time()) - sent_at) > TOLERANCE_SECONDS:
		raise InvalidSignature("Timestamp outside tolerance")

	try:
		key = base64.b64decode(secret.removeprefix("whsec_"))
	except ValueError:
		raise InvalidSignature("Bad signing secret") from None
	signed = f"{msg_id}.{timestamp}.".encode() + body
	expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

	for entry in signatures.split():
		version, _, candidate = entry.partition(",")
		if version == "v1" and hmac.compare_digest(candidate, expected):
			return msg_id
	raise InvalidSignature("Signature mismatch")
