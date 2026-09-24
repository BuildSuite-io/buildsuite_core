# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe

ROUTE = "/procurement/report/rate-check"


def execute():
	"""Tile 'Purchase rate vs estimate' in the Estimation workspace too (matrix: procurement +
	estimation). The report grants Estimator/QS, who can see Estimation but not Procurement — so it
	must be reachable from Estimation for that access to mean anything, and for the report-role
	validation (report roles must fit within a workspace it's tiled in) to hold. Idempotent."""
	settings = frappe.get_single("Workspace Setting")
	if any(r.workspace == "estimation" and (r.route or "").strip() == ROUTE for r in settings.reports):
		return
	settings.append(
		"reports",
		{
			"workspace": "estimation",
			"label": "Purchase rate vs estimate",
			"icon": "chart-bar",
			"route": ROUTE,
			"description": "What you are paying against the QS rate in the Rate Master.",
		},
	)
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.db.commit()  # nosemgrep
