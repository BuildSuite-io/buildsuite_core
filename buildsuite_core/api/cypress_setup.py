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


# dev/test-only fixture password; the function throws unless developer_mode / in_test.
@frappe.whitelist()  # nosemgrep
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
			project = (
				frappe.get_doc(
					{"doctype": "Project", "project_name": "Cypress WO Project", "company": company}
				)
				.insert(ignore_permissions=True)
				.name
			)
		sub = frappe.db.get_value("Supplier", {"supplier_group": "Subcontractor"}, "name")
		if not sub:
			grp = frappe.db.get_value("Supplier Group", {"supplier_group_name": "Subcontractor"}, "name")
			sub = (
				frappe.get_doc(
					{
						"doctype": "Supplier",
						"supplier_name": "Cypress Subcontractor",
						"supplier_group": grp or "Subcontractor",
					}
				)
				.insert(ignore_permissions=True)
				.name
			)

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


@frappe.whitelist()
def ensure_cypress_bills():
	"""Return one draft + one submitted Subcontractor Bill name, for the detail-page action-gating
	e2e (Edit/Submit/Delete on a draft, Cancel on a submitted one). Reuses existing bills — the demo
	carries many — and returns None for a slot that has no record so the spec skips that half rather
	than fail. Read-only; dev/test only."""
	if not (frappe.conf.developer_mode or frappe.flags.in_test):
		frappe.throw(frappe._("ensure_cypress_bills is only available in developer / test mode"))

	return {
		"draft": frappe.db.get_value("Subcontractor Bill", {"docstatus": 0}, "name"),
		"submitted": frappe.db.get_value("Subcontractor Bill", {"docstatus": 1}, "name"),
	}


@frappe.whitelist()
def ensure_cypress_material_request():
	"""Return a DRAFT Material Request name for the MR workflow e2e. With the seeded
	"Material Request Approval" workflow active, its detail should show the workflow's
	"Submit for Approval" transition instead of the plain docstatus Submit. Reuses an existing
	draft; otherwise provisions one with an HSN-coded item so india_compliance doesn't block the
	insert. Returns None if it can't provision (spec skips). Dev/test only."""
	if not (frappe.conf.developer_mode or frappe.flags.in_test):
		frappe.throw(frappe._("ensure_cypress_material_request is only available in developer / test mode"))

	existing = frappe.db.get_value("Material Request", {"docstatus": 0}, "name")
	if existing:
		return existing

	try:
		company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value(
			"Company", {}, "name"
		)
		project = frappe.db.get_value("Project", {"company": company}, "name")
		if not project:
			project = (
				frappe.get_doc(
					{"doctype": "Project", "project_name": "Cypress MR Project", "company": company}
				)
				.insert(ignore_permissions=True)
				.name
			)
		# An HSN-coded item keeps india_compliance from blocking the insert on this GST site.
		item = frappe.db.get_value("Item", {"gst_hsn_code": ["is", "set"]}, "name") or frappe.db.get_value(
			"Item", {}, "name"
		)
		wh = frappe.db.get_value(
			"Warehouse", {"is_group": 0, "company": company}, "name"
		) or frappe.db.get_value("Warehouse", {"is_group": 0}, "name")
		doc = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": company,
				"project": project,
				"schedule_date": frappe.utils.today(),
				"items": [
					{"item_code": item, "qty": 1, "schedule_date": frappe.utils.today(), "warehouse": wh}
				],
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep
		return doc.name
	except Exception:
		frappe.db.rollback()
		return None


@frappe.whitelist()
def ensure_cypress_records():
	"""Return existing record names (reusing demo data) for the comprehensive detail-page
	action-gating e2e (detail_action_gating.cy.js). One key per entity, matching the manifest
	in that spec. A submittable doctype returns a `draft` (docstatus 0) + `submitted`
	(docstatus 1) slot; a master returns a single `one` slot. Any slot with no record comes
	back None so the spec skips it rather than fail. Read-only; dev/test only.

	Shape, e.g.:
	    {"purchaseOrder": {"draft": "...", "submitted": "..."},
	     "machinery": {"one": "..."}, ...}
	"""
	if not (frappe.conf.developer_mode or frappe.flags.in_test):
		frappe.throw(frappe._("ensure_cypress_records is only available in developer / test mode"))

	def one(doctype, filters=None):
		return frappe.db.get_value(doctype, filters or {}, "name")

	def draft_submitted(doctype, base=None):
		base = dict(base or {})
		return {
			"draft": one(doctype, {**base, "docstatus": 0}),
			"submitted": one(doctype, {**base, "docstatus": 1}),
		}

	return {
		# Subcontract
		"subcontractorWorkOrder": draft_submitted("Subcontractor Work Order"),
		# A Draft measurement book so its Edit/Certify buttons render (Certify hides once
		# certified); None → the spec skips rather than open a certified book with no Edit.
		"measurementBook": {"one": one("Measurement Book", {"status": "Draft"})},
		"subcontractor": {"one": one("Supplier", {"supplier_group": "Subcontractor"})},
		# Procurement
		"materialRequest": draft_submitted("Material Request"),
		"purchaseOrder": draft_submitted("Purchase Order"),
		"purchaseReceipt": draft_submitted("Purchase Receipt"),
		# Material Consumption is a Stock Entry of type "Material Issue".
		"materialConsumption": draft_submitted("Stock Entry", {"stock_entry_type": "Material Issue"}),
		# Equipment
		"machinery": {"one": one("Machinery")},
		"machineryUsage": {"one": one("Machinery Usage")},
		# Estimation
		"boq": {"one": one("BOQ")},
		"assembly": {"one": one("Assembly")},
		"estimateTemplate": {"one": one("Estimate Template")},
		"rateMaster": {"one": one("Construction Rate Master")},
		# Workforce
		"fieldEmployee": {"one": one("Employee", {"is_labour": 1})},
		"crew": {"one": one("Crew")},
		"fieldAttendance": draft_submitted("Field Attendance"),
		# Project Finance
		"salesInvoice": draft_submitted("Sales Invoice"),
		"supplierBill": draft_submitted("Purchase Invoice"),
	}


# A persona an admin builds from a role BuildSuite does not ship, and configures by hand — the
# way a site would in Settings > Personas, Role Permission Manager, Workspace Structure and the
# Report's roles. custom_persona_access.cy.js proves such a user gets exactly what was configured.
CUSTOM_ROLE = "Cypress Plant Coordinator"
CUSTOM_PERSONA = "Cypress Plant Coordinator"
CUSTOM_PERSONA_USER = "cypress-plant-coordinator@buildsuite.test"
# DocPerms the admin grants the role, by doctype (ptype -> 1).
CUSTOM_DOCPERMS = {
	"Machinery": {"read": 1, "write": 1, "create": 1, "report": 1, "export": 1, "print": 1},
	"Machinery Type": {"read": 1},  # the type picker on the Machinery form
	# The company picker. Built-in roles get Company (and the other linked masters) from the
	# install-time read mirror, which covers only BuildSuite's own roles — a custom role is given it.
	"Company": {"read": 1},
	"Purchase Order": {"read": 1, "report": 1},  # the data behind the Purchase Register report
}
# Workspaces the role may see (BuildSuite Workspace -> Visible To), and the report it may open.
CUSTOM_WORKSPACES = {"equipment": "full", "procurement": "full"}
CUSTOM_REPORT = "BuildSuite Purchase Register"


@frappe.whitelist()  # nosemgrep
def ensure_cypress_custom_persona(password: str = "Cypress-Suite-2026!"):
	"""Idempotently configure the custom persona + its user for the Cypress suite. Dev/test only.

	bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_custom_persona
	"""
	if not (frappe.conf.developer_mode or frappe.flags.in_test):
		frappe.throw(frappe._("ensure_cypress_custom_persona is only available in developer / test mode"))
	from frappe.permissions import add_permission, update_permission_property

	if not frappe.db.exists("Role", CUSTOM_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": CUSTOM_ROLE, "desk_access": 1}).insert(
			ignore_permissions=True
		)

	# Role Permission Manager: what the role may do on each doctype (only this role is touched).
	for doctype, perms in CUSTOM_DOCPERMS.items():
		add_permission(doctype, CUSTOM_ROLE, 0)
		for ptype in ("read", "write", "create", "delete", "submit", "report", "export", "print"):
			update_permission_property(doctype, CUSTOM_ROLE, 0, ptype, perms.get(ptype, 0), validate=False)

	# Workspace Structure: the sidebar entries the role sees.
	for slug, access in CUSTOM_WORKSPACES.items():
		ws = frappe.get_doc("BuildSuite Workspace", slug)
		if not any(r.role == CUSTOM_ROLE for r in ws.roles):
			ws.append("roles", {"role": CUSTOM_ROLE, "access": access})
			ws.save(ignore_permissions=True)

	# The report's own roles (after the workspace, which the report's validation requires).
	report = frappe.get_doc("Report", CUSTOM_REPORT)
	if not any(r.role == CUSTOM_ROLE for r in report.roles):
		report.append("roles", {"role": CUSTOM_ROLE})
		report.save(ignore_permissions=True)

	# Settings > Personas: a persona carrying only the custom role.
	if not frappe.db.exists("Persona", CUSTOM_PERSONA):
		frappe.get_doc(
			{
				"doctype": "Persona",
				"persona_name": CUSTOM_PERSONA,
				"enabled": 1,
				"roles": [{"role": CUSTOM_ROLE}],
			}
		).insert(ignore_permissions=True)

	# A machine type the spec's Machinery record can point at.
	if not frappe.db.exists("Machinery Type", "Cypress Excavator"):
		frappe.get_doc({"doctype": "Machinery Type", "type_name": "Cypress Excavator"}).insert(
			ignore_permissions=True
		)

	if frappe.db.exists("User", CUSTOM_PERSONA_USER):
		user = frappe.get_doc("User", CUSTOM_PERSONA_USER)
		user.enabled = 1
		user.persona = CUSTOM_PERSONA
		user.first_name, user.last_name = "Casey", "Custom"
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": CUSTOM_PERSONA_USER,
				# Named apart from the persona, so the spec can tell the persona label from the name.
				"first_name": "Casey",
				"last_name": "Custom",
				"enabled": 1,
				"send_welcome_email": 0,
				"persona": CUSTOM_PERSONA,
			}
		)
	user.new_password = password
	user.flags.ignore_password_policy = True
	user.save(ignore_permissions=True)

	frappe.clear_cache()
	# Dev-only helper run via `bench execute`, which does not auto-commit.
	frappe.db.commit()  # nosemgrep
	return {
		"user": CUSTOM_PERSONA_USER,
		"persona": CUSTOM_PERSONA,
		"roles": sorted(r.role for r in frappe.get_doc("User", CUSTOM_PERSONA_USER).roles),
		"machinery_type": "Cypress Excavator",
	}
