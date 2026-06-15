"""Provision deterministic persona test users for the Cypress e2e suite.

Dev/test only. Each user is enabled with a known password and its `persona`
Select set; the `sync_persona_roles` User validate hook then assigns the matching
BuildSuite role automatically. The emails + persona ids mirror PERSONA_USERS in
frontend/cypress/support/commands.js.

Run once before the suite:
    bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users
or with a custom password (matching Cypress `adminPassword` / CYPRESS_ADMIN_PWD):
    bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users --kwargs "{'password': 'secret'}"
"""

import frappe

# persona id (Cypress `loginAs`) -> (email, full_name, User.persona Select value).
# The persona values must match PERSONA_TO_ROLE keys in permissions/setup.py.
CYPRESS_USERS = {
    "admin": ("cypress-admin@buildsuite.test", "Cypress Admin", "BuildSuite Administrator"),
    "pm": ("cypress-pm@buildsuite.test", "Cypress PM", "Project Manager"),
    "estimator": ("cypress-estimator@buildsuite.test", "Cypress Estimator", "Estimator"),
}


@frappe.whitelist()
def ensure_cypress_users(password="Cypress-Suite-2026!"):
    """Idempotently create/refresh the Cypress persona test users. Returns a summary list.

    Password policy is bypassed for these throwaway test accounts so a simple,
    config-shared password works.
    """
    if not (frappe.conf.developer_mode or frappe.flags.in_test):
        frappe.throw("ensure_cypress_users is only available in developer / test mode")

    summary = []
    for persona_id, (email, full_name, persona) in CYPRESS_USERS.items():
        first, _, last = full_name.partition(" ")
        if frappe.db.exists("User", email):
            doc = frappe.get_doc("User", email)
            doc.enabled = 1
            doc.persona = persona
            doc.new_password = password
            action = "updated"
        else:
            doc = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": first or full_name,
                "last_name": last,
                "enabled": 1,
                "send_welcome_email": 0,
                "persona": persona,
                "new_password": password,
            })
            action = "created"
        doc.flags.ignore_password_policy = True
        doc.save(ignore_permissions=True) if action == "updated" else doc.insert(ignore_permissions=True)
        summary.append(f"{action} {persona_id}: {email} (persona={persona})")

    frappe.db.commit()
    return summary
