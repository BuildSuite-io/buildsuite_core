# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed one ERPNext Project Template per construction Project Category.

Each template extends ERPNext's native Project Template with a project_category,
default Work Packages, and default Stages (our custom fields), plus the native
task list. Tasks are template Tasks (is_template=1) whose ERPNext start/duration
(days) drive project scheduling; each task row carries a work_package_code that
create-from-template resolves to a real Work Package. Data mirrors the prototype's
projectTypeTemplates.js. Idempotent — skips a template that already exists.
"""

import frappe

# category -> {work_packages, stages, tasks}
TEMPLATES = {
	"Commercial": {
		"work_packages": [
			("WP-FND", "Foundation Works", 5000000, 1, "Excavation, PCC, raft & footing pours."),
			("WP-STRUCT", "Superstructure", 15000000, 2, "Vertical RCC frame across all floors."),
			("WP-MEP", "MEP Rough-in", 6000000, 3, "Electrical, plumbing, HVAC rough-in across floors."),
			("WP-FIN", "Finishing", 8000000, 4, "Masonry, plaster, flooring, paint, facade."),
			("WP-HND", "Handover", 500000, 5, "Snagging, statutory clearances, client handover."),
		],
		"stages": [
			("Foundation", 0, 60, 8, "Earthwork, excavation, PCC, and raft foundation."),
			("Substructure", 45, 120, 12, "Basement walls, raft cap, ground-floor slab."),
			("Superstructure", 90, 240, 28, "RCC frame — columns, beams, slabs across all floors."),
			("MEP rough-in", 180, 300, 16, "Electrical conduits, plumbing rough-in, HVAC ducts."),
			("Finishing", 240, 360, 22, "Masonry, plaster, flooring, painting, facade."),
			("Handover", 350, 380, 4, "Snagging, statutory clearances, client handover."),
		],
		# (work_package_code, subject, priority, hours, stage)
		"tasks": [
			("WP-FND", "Earthwork excavation", "High", 240, "Foundation"),
			("WP-FND", "PCC laying", "Medium", 120, "Foundation"),
			("WP-FND", "Raft foundation casting", "High", 400, "Foundation"),
			("WP-STRUCT", "Column casting — Level 1 to 5", "High", 800, "Superstructure"),
			("WP-STRUCT", "Slab casting — Level 1 to 5", "High", 720, "Superstructure"),
			("WP-MEP", "Electrical conduit laying", "Medium", 320, "MEP rough-in"),
			("WP-MEP", "Plumbing rough-in", "Medium", 280, "MEP rough-in"),
			("WP-FIN", "Internal plaster", "Medium", 360, "Finishing"),
			("WP-FIN", "Floor tiling", "Medium", 240, "Finishing"),
			("WP-FIN", "Painting", "Low", 180, "Finishing"),
			("WP-HND", "Snagging walkthrough", "High", 40, "Handover"),
			("WP-HND", "Occupancy certificate", "High", 20, "Handover"),
		],
	},
	"Residential": {
		"work_packages": [
			("WP-FND", "Foundation Works", 4000000, 1, "Excavation, PCC, raft foundation for the tower."),
			("WP-STRUCT", "Tower Superstructure", 12000000, 2, "RCC frame for the residential tower."),
			("WP-MEP", "MEP Rough-in", 5000000, 3, "Electrical, plumbing, gas piping rough-in per unit."),
			("WP-FIT", "Unit Fit-out", 9000000, 4, "Joinery, kitchen, bath, internal finishes per unit."),
			("WP-AMEN", "Amenities", 2500000, 5, "Clubhouse, landscaping, common areas."),
		],
		"stages": [
			("Foundation", 0, 60, 6, "Earthwork, excavation, PCC, and raft foundation."),
			("Substructure", 45, 120, 10, "Basement walls, raft cap, ground-floor slab."),
			("Superstructure", 90, 240, 24, "RCC frame across all floors."),
			("MEP rough-in", 180, 300, 14, "Electrical conduits, plumbing rough-in per unit."),
			("Finishing", 240, 360, 20, "Fit-out, flooring, painting, amenities."),
			("Handover", 350, 380, 4, "Snagging, statutory clearances, client handover."),
		],
		"tasks": [
			("WP-FND", "Earthwork excavation", "High", 200, "Foundation"),
			("WP-FND", "Raft foundation casting", "High", 360, "Foundation"),
			("WP-STRUCT", "Tower column casting", "High", 720, "Superstructure"),
			("WP-STRUCT", "Tower slab casting", "High", 640, "Superstructure"),
			("WP-MEP", "Conduit + plumbing per unit", "Medium", 480, "MEP rough-in"),
			("WP-FIT", "Wall plaster + putty", "Medium", 320, "Finishing"),
			("WP-FIT", "Floor tiling per unit", "Medium", 280, "Finishing"),
			("WP-FIT", "Joinery + kitchen fit-out", "Medium", 360, "Finishing"),
			("WP-FIT", "Painting", "Low", 200, "Finishing"),
			("WP-AMEN", "Clubhouse finishing", "Medium", 240, "Finishing"),
			("WP-AMEN", "Landscaping", "Low", 160, "Finishing"),
		],
	},
	"Infrastructure": {
		"work_packages": [
			("WP-SITE", "Site Preparation", 6000000, 1, "Grading, mass excavation, utility diversion, site access."),
			("WP-PILE", "Piling & Foundations", 18000000, 2, "Pile foundations, pile caps, footings."),
			("WP-STRUCT", "Civil Structure", 32000000, 3, "Columns, decks, retaining walls, station box."),
			("WP-COMM", "Commissioning", 10000000, 4, "Finishes, signalling fit-out, testing, commissioning."),
		],
		"stages": [
			("Site Prep", 0, 90, 4, "Grading, mass excavation, utility diversion, site access."),
			("Foundation", 60, 180, 6, "Pile foundations, pile caps, footings."),
			("Structure", 150, 330, 12, "Columns, decks, retaining walls."),
			("Finishing & Commissioning", 300, 400, 4, "Finishes, signalling fit-out, testing, commissioning."),
		],
		"tasks": [
			("WP-SITE", "Site grading", "High", 320, "Site Prep"),
			("WP-SITE", "Utility diversion", "High", 240, "Site Prep"),
			("WP-PILE", "Pile installation", "High", 800, "Foundation"),
			("WP-PILE", "Pile cap casting", "High", 400, "Foundation"),
			("WP-STRUCT", "Column casting", "High", 960, "Structure"),
			("WP-STRUCT", "Deck casting", "High", 720, "Structure"),
			("WP-STRUCT", "Retaining wall construction", "Medium", 540, "Structure"),
			("WP-COMM", "Signalling fit-out", "High", 480, "Finishing & Commissioning"),
			("WP-COMM", "Testing & commissioning", "High", 320, "Finishing & Commissioning"),
		],
	},
}


def _template_task(subject, priority, hours):
	"""A reusable ERPNext template Task (is_template=1). start/duration are in days —
	duration derives from the estimated hours at 8h/day, all beginning at day 0."""
	return frappe.get_doc(
		{
			"doctype": "Task",
			"subject": subject,
			"is_template": 1,
			"priority": priority,
			"expected_time": hours,
			"start": 0,
			"duration": max(1, round(hours / 8)),
		}
	).insert(ignore_permissions=True)


def seed_project_templates():
	created = []
	for category, tpl in TEMPLATES.items():
		if not frappe.db.exists("Project Category", category):
			continue
		if frappe.db.exists("Project Template", category):
			continue

		doc = frappe.new_doc("Project Template")
		doc.name = category  # Project Template autoname is "Prompt"
		doc.project_category = category

		for code, name, budget, order, desc in tpl["work_packages"]:
			doc.append(
				"custom_work_packages",
				{
					"code": code,
					"work_package_name": name,
					"budget": budget,
					"sort_order": order,
					"description": desc,
				},
			)
		for stage_name, start, end, count, desc in tpl["stages"]:
			doc.append(
				"custom_stages",
				{
					"stage_name": stage_name,
					"offset_start_days": start,
					"offset_end_days": end,
					"planned_task_count": count,
					"planned_completion_pct": 100,
					"description": desc,
				},
			)
		for wp_code, subject, priority, hours, stage in tpl["tasks"]:
			task = _template_task(subject, priority, hours)
			doc.append(
				"tasks",
				{
					"task": task.name,
					"custom_work_package_code": wp_code,
					"custom_stage": stage,
				},
			)

		doc.insert(ignore_permissions=True)
		created.append(category)

	return created
