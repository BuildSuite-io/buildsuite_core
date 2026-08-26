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

# persona id (Cypress `loginAs`) -> (email, full_name, User.persona value).
# The persona id matches PERSONA_CAPS / the role slug in frontend/src/data/roles.js and
# PERSONA_USERS in frontend/cypress/support/commands.js (keep the three in sync). The
# persona value must match a Persona record name (see the Persona master / seed_personas).
CYPRESS_USERS = {
	"director": ("cypress-director@buildsuite.test", "Cypress Director", "Director / Owner"),
	"pm": ("cypress-pm@buildsuite.test", "Cypress PM", "Project Manager"),
	"estimator": ("cypress-estimator@buildsuite.test", "Cypress Estimator", "Estimator"),
	"qs": ("cypress-qs@buildsuite.test", "Cypress QS", "Quantity Surveyor"),
	"site-engineer": ("cypress-site-engineer@buildsuite.test", "Cypress Site Engineer", "Site Engineer"),
	"foreman": ("cypress-foreman@buildsuite.test", "Cypress Foreman", "Foreman / Supervisor"),
	"procurement": ("cypress-procurement@buildsuite.test", "Cypress Procurement", "Procurement Officer"),
	"store-keeper": ("cypress-store-keeper@buildsuite.test", "Cypress Store Keeper", "Store Keeper"),
	"accountant": ("cypress-accountant@buildsuite.test", "Cypress Accountant", "Accountant"),
	"hr-manager": ("cypress-hr-manager@buildsuite.test", "Cypress HR Manager", "HR Manager"),
	"admin": ("cypress-admin@buildsuite.test", "Cypress Admin", "System Manager (Admin)"),
	"bsa": ("cypress-bsa@buildsuite.test", "Cypress BSA", "BuildSuite Administrator"),
}


@frappe.whitelist()
def ensure_cypress_users(password: str = "Cypress-Suite-2026!"):
	"""Idempotently create/refresh the Cypress persona test users. Returns a summary list.

	Password policy is bypassed for these throwaway test accounts so a simple,
	config-shared password works.
	"""
	if not (frappe.conf.developer_mode or frappe.flags.in_test):
		frappe.throw(frappe._("ensure_cypress_users is only available in developer / test mode"))

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
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": first or full_name,
					"last_name": last,
					"enabled": 1,
					"send_welcome_email": 0,
					"persona": persona,
					"new_password": password,
				}
			)
			action = "created"
		doc.flags.ignore_password_policy = True
		doc.save(ignore_permissions=True) if action == "updated" else doc.insert(ignore_permissions=True)
		summary.append(f"{action} {persona_id}: {email} (persona={persona})")

	# Dev-only helper run via `bench execute`, which does not auto-commit; the
	# explicit commit persists the provisioned users.
	frappe.db.commit()  # nosemgrep
	return summary


@frappe.whitelist()
def ensure_cypress_work_order():
	"""Return the name of a SUBMITTED Subcontractor Work Order, for detail-page e2e tests that
	need a real record (e.g. the cross-entity create-button gating spec). Reuses any existing
	submitted WO; otherwise provisions one (demo project + subcontractor + a line, then submit).
	Idempotent. Returns the WO name, or None if it couldn't provision one (spec skips)."""
	if not (frappe.conf.developer_mode or frappe.flags.in_test):
		frappe.throw(frappe._("ensure_cypress_work_order is only available in developer / test mode"))

	existing = frappe.db.get_value("Subcontractor Work Order", {"docstatus": 1}, "name")
	if existing:
		return existing

	try:
		from buildsuite_core.api import subcontract as sc

		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
			"Company", {}, "name"
		)
		project = frappe.db.get_value("Project", {"company": company}, "name")
		if not project:
			project = frappe.get_doc(
				{"doctype": "Project", "project_name": "Cypress WO Project", "company": company}
			).insert(ignore_permissions=True).name
		sub = frappe.db.get_value("Supplier", {"supplier_group": "Subcontractor"}, "name")
		if not sub:
			grp = frappe.db.get_value("Supplier Group", {"supplier_group_name": "Subcontractor"}, "name")
			sub = frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": "Cypress Subcontractor",
					"supplier_group": grp or "Subcontractor",
				}
			).insert(ignore_permissions=True).name

		out = sc.save_work_order(
			subcontractor=sub,
			project=project,
			lines=frappe.as_json([{"scope": "Tiling", "uom": "Nos", "qty": 10, "rate": 100}]),
		)
		doc = frappe.get_doc("Subcontractor Work Order", out["name"])
		doc.submit()
		frappe.db.commit()  # nosemgrep
		return doc.name
	except Exception:
		frappe.db.rollback()
		return None
