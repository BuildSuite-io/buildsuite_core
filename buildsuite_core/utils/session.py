"""Run a block as Administrator without corrupting the caller's live web session.

frappe.set_user() is built for scripts, not mid-request elevation: besides switching the
current user it also overwrites frappe.session.sid with the username and wipes
frappe.session.data. Calling set_user back to the caller restores `.user`, but leaves
`sid` = <email> (not the browser's real session id) and `data` = {}. The session Frappe
persists at request end then no longer maps the browser's cookie to a valid user, so the
NEXT request fails with "user not found" and logs the user out — after the write has
already committed, which is why the created record is there once you log back in.

as_administrator() elevates for the block, then restores the caller's user AND the session
identity (sid + data) that set_user clobbered, leaving the live session exactly as found.
"""

from contextlib import contextmanager

import frappe


@contextmanager
def as_administrator():
	"""Temporarily run as Administrator, restoring the caller's full session afterwards.

	Needed for server-side plumbing (e.g. building a bill/invoice that reads the party's
	Address) that frappe.permissions.has_permission only clears for Administrator — it honours
	neither frappe.flags.ignore_permissions nor the doc-level flag for those nested reads.
	"""
	user = frappe.session.user
	sid = frappe.session.sid
	data = frappe.session.data
	try:
		frappe.set_user("Administrator")
		yield
	finally:
		frappe.set_user(user)
		# set_user clobbers these two; put back the real session identity so request-end
		# persistence doesn't invalidate the browser's session and log the user out.
		frappe.local.session.sid = sid
		frappe.local.session.data = data
