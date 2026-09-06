"""Promote existing persona users to System User.

A BuildSuite persona user works in the Desk / SPA, which needs user_type="System User". A persona
user created as a Website User can't log in — and the workaround (adding System Manager) over-grants
(System Manager unlocks the full Project Finance workspace, etc.). The User validate hook now
promotes on save; this converges existing sites.
"""

import frappe


def execute():
	users = frappe.get_all(
		"User",
		filters={"persona": ["is", "set"], "user_type": "Website User", "name": ["not in", ("Guest",)]},
		pluck="name",
	)
	for u in users:
		frappe.db.set_value("User", u, "user_type", "System User", update_modified=False)
	if users:
		frappe.clear_cache()
		print(f"promote_persona_users_to_system_user: promoted {len(users)} persona user(s)")
