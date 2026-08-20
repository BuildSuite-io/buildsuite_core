import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import flt


@frappe.whitelist()
def get_dashboard() -> dict:
	return {
		"machines": frappe.db.count("Machinery"),
		"owned": frappe.db.count("Machinery", {"ownership": "Owned"}),
		"hired": frappe.db.count("Machinery", {"ownership": "Hired"}),
		"equipment_cost": _equipment_cost(),
		"recent_usage": _recent_usage(),
		"register": _register(),
	}


def _equipment_cost() -> float:
	mu = frappe.qb.DocType("Machinery Usage")
	# qty * rate + fuel, summed across all usage rows
	row = (frappe.qb.from_(mu).select(Sum(mu.quantity * mu.rate), Sum(mu.fuel_cost))).run()[0]
	return flt(row[0]) + flt(row[1])


def _name_map(doctype, value_field, ids):
	"""{docname: value_field} for the given ids, in one query. Resolved server-side so a caller
	that can read Machinery Usage but not Machinery / Task still gets readable labels (the
	client used to run a second list query that came back empty under such perms — ISS-142)."""
	ids = [i for i in set(ids) if i]
	if not ids:
		return {}
	return {
		r.name: r.get(value_field)
		for r in frappe.get_all(doctype, filters={"name": ["in", ids]}, fields=["name", value_field])
	}


def _recent_usage() -> list[dict]:
	rows = frappe.get_list(
		"Machinery Usage",
		fields=["name", "machine", "project", "date", "quantity", "unit", "rate", "fuel_cost"],
		order_by="date desc",
		limit=6,
	)
	machine_names = _name_map("Machinery", "machinery_name", [r.machine for r in rows])
	for r in rows:
		r["machine_name"] = machine_names.get(r.machine) or r.machine
		r["total"] = flt(r.quantity) * flt(r.rate) + flt(r.fuel_cost)
	return rows


@frappe.whitelist()
def machinery_usage_report() -> list[dict]:
	"""Machinery Utilisation report — every usage entry with its machine, project and task
	resolved to readable names and the total cost (qty * rate + fuel) computed server-side, so
	the report renders without any second lookup. Newest first."""
	rows = frappe.get_list(
		"Machinery Usage",
		fields=["name", "machine", "project", "task", "date", "quantity", "unit", "rate", "fuel_cost"],
		order_by="date desc",
		limit_page_length=0,
	)
	machine_names = _name_map("Machinery", "machinery_name", [r.machine for r in rows])
	project_names = _name_map("Project", "project_name", [r.project for r in rows])
	task_subjects = _name_map("Task", "subject", [r.task for r in rows])
	for r in rows:
		r["machine_name"] = machine_names.get(r.machine) or r.machine
		r["project_name"] = project_names.get(r.project) or r.project
		r["task_subject"] = task_subjects.get(r.task) or r.task
		r["total"] = flt(r.quantity) * flt(r.rate) + flt(r.fuel_cost)
	return rows


@frappe.whitelist()
def machinery_register() -> list[dict]:
	"""Equipment Register report — owned + hired plant with their rates. Ordered by name."""
	return frappe.get_list(
		"Machinery",
		fields=[
			"name",
			"machinery_name",
			"machinery_type",
			"ownership",
			"rate",
			"rate_unit",
			"owner_vendor",
			"status",
		],
		order_by="machinery_name asc",
		limit_page_length=0,
	)


def _register() -> list[dict]:
	return frappe.get_list(
		"Machinery",
		fields=["name", "machinery_name", "machinery_type", "ownership", "rate", "rate_unit", "status"],
		order_by="machinery_name asc",
		limit=6,
	)
