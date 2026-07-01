"""Seed a realistic Estimation demo: users -> project -> work packages ->
rate master -> assemblies -> estimate template -> BOQ master (groups/items/
sub-items), wired end to end so /core shows a full, dependency-linked estimate.

Dev/demo only (guarded on developer_mode). Idempotent: masters are
get-or-create by code, and the demo project's BOQ tree is rebuilt on every run.

Run:
    bench --site bs.local execute buildsuite_core.api.estimation_seed.seed_estimation_demo
Tear down:
    bench --site bs.local execute buildsuite_core.api.estimation_seed.unseed_estimation_demo
"""

import frappe
from frappe.utils import add_months, today

from buildsuite_core.api import boq as boq_api

DEMO_PASSWORD = "BuildSuite-Demo-2026!"
PROJECT_CODE = "DEMO-EST-001"

# --- persona users (persona must match PERSONA_TO_ROLE keys) ------------------
DEMO_USERS = {
	"director": ("demo-director@buildsuite.demo", "Dana Director", "Director / Owner"),
	"pm": ("demo-pm@buildsuite.demo", "Paul Manager", "Project Manager"),
	"estimator": ("demo-estimator@buildsuite.demo", "Esther Estimator", "Estimator"),
	"qs": ("demo-qs@buildsuite.demo", "Quinn Surveyor", "Quantity Surveyor"),
}

UOMS = ["Cubic Meter", "Square Meter", "Kg", "Bag", "Nos", "Day"]

# rate_code -> (name, category, uom, current_rate)
RATES = {
	"CEM-OPC": ("Cement OPC 42.5 (50kg)", "Material", "Bag", 5.50),
	"SAND-SHARP": ("Sharp Sand", "Material", "Cubic Meter", 18.00),
	"AGG-20": ("Coarse Aggregate 20mm", "Material", "Cubic Meter", 22.00),
	"REBAR-Y16": ("Reinforcement Bar Y16", "Material", "Kg", 0.95),
	"PLY-18": ("Formwork Plywood 18mm", "Material", "Square Meter", 12.00),
	"BLK-200": ("Hollow Block 200mm", "Material", "Nos", 1.20),
	"LAB-MASON": ("Mason", "Labour", "Day", 35.00),
	"LAB-STEEL": ("Steel Fixer", "Labour", "Day", 38.00),
	"LAB-CARP": ("Carpenter (Formwork)", "Labour", "Day", 36.00),
	"LAB-GEN": ("General Labourer", "Labour", "Day", 22.00),
	"EQ-MIXER": ("Concrete Mixer 0.5m3", "Equipment", "Day", 45.00),
	"EQ-VIB": ("Poker Vibrator", "Equipment", "Day", 15.00),
}

# assembly_code -> (name, category, uom, [(resource_code, coefficient), ...])
ASSEMBLIES = {
	"ASM-C25": (
		"In-situ Concrete C25/30",
		"Concrete",
		"Cubic Meter",
		[("CEM-OPC", 7.0), ("SAND-SHARP", 0.5), ("AGG-20", 0.8),
		 ("LAB-MASON", 0.3), ("LAB-GEN", 0.8), ("EQ-MIXER", 0.15), ("EQ-VIB", 0.1)],
	),
	"ASM-REBAR": (
		"Reinforcement Fixing (Y16)",
		"Reinforcement",
		"Kg",
		[("REBAR-Y16", 1.05), ("LAB-STEEL", 0.02)],
	),
	"ASM-FORM": (
		"Formwork to Columns & Beams",
		"General",
		"Square Meter",
		[("PLY-18", 0.30), ("LAB-CARP", 0.25), ("LAB-GEN", 0.10)],
	),
	"ASM-BLK": (
		"Blockwork 200mm",
		"Masonry",
		"Square Meter",
		[("BLK-200", 12.5), ("LAB-MASON", 0.20), ("LAB-GEN", 0.15)],
	),
}

# work_package_name -> code
WORK_PACKAGES = [
	("Substructure", "WP-SUB"),
	("Superstructure", "WP-SUP"),
	("Finishes", "WP-FIN"),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _ensure_uoms():
	for name in UOMS:
		if not frappe.db.exists("UOM", name):
			frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert(ignore_permissions=True)


def _ensure_user(email, full_name, persona):
	first, _, last = full_name.partition(" ")
	if frappe.db.exists("User", email):
		doc = frappe.get_doc("User", email)
		doc.enabled = 1
		doc.persona = persona
	else:
		doc = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": first,
			"last_name": last,
			"enabled": 1,
			"send_welcome_email": 0,
			"persona": persona,
			"new_password": DEMO_PASSWORD,
		})
	doc.flags.ignore_password_policy = True
	doc.save(ignore_permissions=True)
	return email


def _ensure_rate(code):
	name, category, uom, rate = RATES[code]
	if frappe.db.exists("Construction Rate Master", code):
		return code
	frappe.get_doc({
		"doctype": "Construction Rate Master",
		"rate_code": code,
		"rate_name": name,
		"category": category,
		"uom": uom,
		"current_rate": rate,
	}).insert(ignore_permissions=True)
	return code


def _ensure_assembly(code):
	name, category, uom, comps = ASSEMBLIES[code]
	if frappe.db.exists("Assembly", code):
		return code
	doc = frappe.get_doc({
		"doctype": "Assembly",
		"assembly_code": code,
		"assembly_name": name,
		"category": category,
		"uom": uom,
	})
	for resource_code, coeff in comps:
		doc.append("components", {
			"resource": resource_code,
			"resource_name": RATES[resource_code][0],
			"coefficient": coeff,
			"uom": RATES[resource_code][2],
		})
	doc.insert(ignore_permissions=True)  # validate() prices components + rate_per_unit
	return code


def _ensure_template():
	code = "TPL-COMM-SHELL"
	if frappe.db.exists("Estimate Template", code):
		return code
	project_type = "Commercial" if frappe.db.exists("Project Type", "Commercial") else None
	doc = frappe.get_doc({
		"doctype": "Estimate Template",
		"template_code": code,
		"template_name": "Commercial RC Frame — Shell & Core",
		"description": "Reusable shell-and-core skeleton for a commercial RC-frame building.",
		"project_type": project_type,
		"enabled": 1,
		"rows": [
			{"group_name": "Substructure", "line_type": "Assembly", "assembly": "ASM-C25",
			 "description": "Foundation concrete C25/30", "placeholder_qty": 120, "uom": "Cubic Meter", "cost_head": "Material"},
			{"group_name": "Substructure", "line_type": "Assembly", "assembly": "ASM-REBAR",
			 "description": "Reinforcement to foundations", "placeholder_qty": 9000, "uom": "Kg", "cost_head": "Material"},
			{"group_name": "Superstructure", "line_type": "Assembly", "assembly": "ASM-C25",
			 "description": "Columns, beams & slabs concrete", "placeholder_qty": 480, "uom": "Cubic Meter", "cost_head": "Material"},
			{"group_name": "Superstructure", "line_type": "Assembly", "assembly": "ASM-FORM",
			 "description": "Formwork to frame", "placeholder_qty": 2600, "uom": "Square Meter", "cost_head": "Material"},
			{"group_name": "Finishes", "line_type": "Assembly", "assembly": "ASM-BLK",
			 "description": "200mm blockwork walls", "placeholder_qty": 3400, "uom": "Square Meter", "cost_head": "Material"},
			{"group_name": "Finishes", "line_type": "Resource", "resource": "LAB-GEN",
			 "description": "General site cleaning & handover", "placeholder_qty": 200, "uom": "Day", "cost_head": "Labour"},
		],
	})
	doc.insert(ignore_permissions=True)
	return code


def _ensure_project(company, pm):
	name = frappe.db.get_value("Project", {"custom_project_id": PROJECT_CODE}, "name")
	if name:
		return frappe.get_doc("Project", name)
	start = today()
	doc = frappe.get_doc({
		"doctype": "Project",
		"project_name": "Riverside Commercial Tower",
		"custom_project_id": PROJECT_CODE,
		"project_status": "Ongoing",
		"company": company,
		"is_group": 0,
		"expected_start_date": start,
		"expected_end_date": add_months(start, 18),
		"project_manager": pm,          # auto-adds PM to the team
	})
	doc.insert(ignore_permissions=True)
	return doc


def _ensure_team(project_doc, members):
	existing = {r.user for r in (project_doc.custom_team_members or [])}
	changed = False
	for user in members:
		if user not in existing:
			project_doc.append("custom_team_members", {"user": user})
			changed = True
	if changed:
		project_doc.save(ignore_permissions=True)


def _ensure_work_packages(project):
	wp_by_name = {}
	start = frappe.db.get_value("Project", project, "expected_start_date")
	for i, (wp_name, code) in enumerate(WORK_PACKAGES):
		existing = frappe.db.get_value("Work Package", {"project": project, "work_package_name": wp_name}, "name")
		if existing:
			wp_by_name[wp_name] = existing
			continue
		doc = frappe.get_doc({
			"doctype": "Work Package",
			"project": project,
			"work_package_name": wp_name,
			"code": code,
			"status": "Planned",
			"start_date": add_months(start, i * 4),
			"end_date": add_months(start, i * 4 + 5),
		}).insert(ignore_permissions=True)
		wp_by_name[wp_name] = doc.name
	return wp_by_name


def _ensure_task(project, wp, subject, pct):
	name = frappe.db.get_value("Task", {"project": project, "subject": subject}, "name")
	if not name:
		name = frappe.get_doc({
			"doctype": "Task",
			"subject": subject,
			"project": project,
			"work_package": wp,
			"task_status": "In Progress",
		}).insert(ignore_permissions=True).name
	if not frappe.db.exists("Task Progress Entry", {"task": name}):
		frappe.get_doc({
			"doctype": "Task Progress Entry",
			"task": name,
			"entry_date": today(),
			"cumulative_progress": pct,
		}).insert(ignore_permissions=True)
	return name


def _rebuild_boq(project, company, prepared_by, wp_by_name, task_for_columns):
	# Wipe any prior demo BOQ so re-runs are clean (on_trash cascades the tree).
	for old in frappe.get_all("BOQ", filters={"project": project}, pluck="name"):
		frappe.delete_doc("BOQ", old, force=True, ignore_permissions=True)

	boq = frappe.get_doc({
		"doctype": "BOQ",
		"project": project,
		"company": company,
		"title": "Tender BOQ — Rev 1",
		"revision": 1,
		"status": "Draft",
		"prepared_by": prepared_by,
		"prepared_date": today(),
		"margin_rate": 15.0,
		"tax_rate": 7.5,
	}).insert(ignore_permissions=True)

	# groups: code -> (name, group doc)
	groups = {}
	for code, gname in [("A", "Substructure"), ("B", "Superstructure"), ("C", "Finishes")]:
		g = frappe.get_doc({
			"doctype": "BOQ Group",
			"boq": boq.name,
			"code": code,
			"group_name": gname,
			"idx_order": ord(code) - ord("A") + 1,
		}).insert(ignore_permissions=True)
		groups[code] = g.name

	def assembly_item(group_code, code, desc, assembly, driving_qty, wp, task=None):
		item = frappe.get_doc({
			"doctype": "BOQ Item",
			"boq": boq.name,
			"boq_group": groups[group_code],
			"code": code,
			"description": desc,
			"unit": ASSEMBLIES[assembly][2],
			"planned_qty": driving_qty,
			"driving_qty": driving_qty,
			"quantity_source": "Assembly",
			"assembly": assembly,
			"work_package": wp,
			"task": task,
			"cost_head": "Material",
		}).insert(ignore_permissions=True)
		boq_api.explode_item(item.name)  # snapshots sub-items + sets item.rate
		return item.name

	def manual_item(group_code, code, desc, unit, qty, rate, wp, cost_head="Material"):
		frappe.get_doc({
			"doctype": "BOQ Item",
			"boq": boq.name,
			"boq_group": groups[group_code],
			"code": code,
			"description": desc,
			"unit": unit,
			"planned_qty": qty,
			"rate": rate,
			"quantity_source": "Manual",
			"work_package": wp,
			"cost_head": cost_head,
		}).insert(ignore_permissions=True)

	sub = wp_by_name["Substructure"]
	sup = wp_by_name["Superstructure"]
	fin = wp_by_name["Finishes"]

	assembly_item("A", "A1", "Foundation & pile-cap concrete C25/30", "ASM-C25", 120, sub)
	assembly_item("A", "A2", "Reinforcement to foundations", "ASM-REBAR", 9000, sub)
	manual_item("A", "A3", "Blinding concrete under footings", "Cubic Meter", 40, 85.0, sub)

	assembly_item("B", "B1", "Columns, beams & slabs concrete C25/30", "ASM-C25", 480, sup, task=task_for_columns)
	assembly_item("B", "B2", "Reinforcement to frame", "ASM-REBAR", 52000, sup)
	assembly_item("B", "B3", "Formwork to frame", "ASM-FORM", 2600, sup)

	assembly_item("C", "C1", "200mm blockwork walls", "ASM-BLK", 3400, fin)
	manual_item("C", "C2", "Allowance — external works & landscaping", "Nos", 1, 45000.0, fin, cost_head="Other")

	# Pull actuals from the linked task's live progress.
	boq_api.recalculate_actuals(boq.name)
	boq.reload()
	return boq


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------
def _guard():
	if not (frappe.conf.developer_mode or frappe.conf.allow_tests or frappe.flags.in_test):
		frappe.throw(frappe._("This seed helper is only available in developer / test mode"))


@frappe.whitelist()
def seed_estimation_demo():
	_guard()

	company = frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw(frappe._("No Company found — install ERPNext and create a Company first."))

	_ensure_uoms()
	users = {k: _ensure_user(*v) for k, v in DEMO_USERS.items()}
	for code in RATES:
		_ensure_rate(code)
	for code in ASSEMBLIES:
		_ensure_assembly(code)
	template = _ensure_template()

	project = _ensure_project(company, users["pm"])
	_ensure_team(project, [users["director"], users["estimator"], users["qs"]])
	wp_by_name = _ensure_work_packages(project.name)
	task = _ensure_task(project.name, wp_by_name["Superstructure"], "Cast columns — Level 1", 25)
	boq = _rebuild_boq(project.name, company, users["estimator"], wp_by_name, task)

	frappe.db.commit()  # nosemgrep - dev helper run via bench execute
	summary = {
		"company": company,
		"users": users,
		"project": project.name,
		"work_packages": wp_by_name,
		"rate_master": len(RATES),
		"assemblies": {c: frappe.db.get_value("Assembly", c, "rate_per_unit") for c in ASSEMBLIES},
		"estimate_template": template,
		"boq": boq.name,
		"boq_planned_amount": boq.planned_amount,
		"boq_margin_amount": boq.margin_amount,
		"boq_tax_amount": boq.tax_amount,
		"boq_total": boq.total,
		"boq_actual_amount": boq.actual_amount,
		"password": DEMO_PASSWORD,
	}
	print(frappe.as_json(summary))  # noqa: T201 - visible in bench execute output
	return summary


@frappe.whitelist()
def unseed_estimation_demo():
	"""Remove the demo project (cascades BOQ/WP/Task). Leaves shared masters + users."""
	_guard()
	name = frappe.db.get_value("Project", {"custom_project_id": PROJECT_CODE}, "name")
	if name:
		frappe.delete_doc("Project", name, force=True, ignore_permissions=True)
	frappe.db.commit()  # nosemgrep - dev helper run via bench execute
	return {"deleted_project": name}
