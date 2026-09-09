# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Cost Code Variance — Planned vs Committed vs Actual, and the variance, for every BOQ cost code
on a project. Wraps ``cost_vs_budget_by_cost_code`` so the register and the project cost view stay
in lock-step. A Project filter is required — variance is only meaningful against one project's
Approved BOQ."""

import frappe
from frappe import _

from buildsuite_core.api.cost_report import cost_vs_budget_by_cost_code


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{"label": _("Cost Code"), "fieldname": "code", "fieldtype": "Data", "width": 110},
		{"label": _("Name"), "fieldname": "cost_name", "fieldtype": "Data", "width": 220},
		{"label": _("Cost Type"), "fieldname": "cost_type", "fieldtype": "Data", "width": 120},
		{"label": _("Planned"), "fieldname": "planned", "fieldtype": "Currency", "width": 120},
		{"label": _("Committed"), "fieldname": "committed", "fieldtype": "Currency", "width": 120},
		{"label": _("Actual"), "fieldname": "actual", "fieldtype": "Currency", "width": 120},
		{"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "width": 120},
		{"label": _("Variance %"), "fieldname": "variance_pct", "fieldtype": "Percent", "width": 100},
	]
	if not filters.get("project"):
		return columns, []

	result = cost_vs_budget_by_cost_code(filters.get("project"))
	data = [
		{
			"code": r.get("code"),
			"cost_name": r.get("name"),
			"cost_type": r.get("costType"),
			"planned": r.get("planned"),
			"committed": r.get("committed"),
			"actual": r.get("actual"),
			"variance": r.get("variance"),
			"variance_pct": r.get("variancePct"),
		}
		for r in result.get("rows", [])
	]
	return columns, data
