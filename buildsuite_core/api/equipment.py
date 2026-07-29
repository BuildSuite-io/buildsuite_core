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
	row = (
		frappe.qb.from_(mu).select(Sum(mu.quantity * mu.rate), Sum(mu.fuel_cost))
	).run()[0]
	return flt(row[0]) + flt(row[1])


def _recent_usage() -> list[dict]:
	rows = frappe.get_list(
		"Machinery Usage",
		fields=["name", "machine", "project", "date", "quantity", "unit", "rate", "fuel_cost"],
		order_by="date desc",
		limit=6,
	)
	for r in rows:
		r["total"] = flt(r.quantity) * flt(r.rate) + flt(r.fuel_cost)
	return rows


def _register() -> list[dict]:
	return frappe.get_list(
		"Machinery",
		fields=["name", "machinery_name", "machinery_type", "ownership", "rate", "rate_unit", "status"],
		order_by="machinery_name asc",
		limit=6,
	)
