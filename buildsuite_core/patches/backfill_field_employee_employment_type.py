# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Stamp the 'Labour' Employment Type on existing field employees.

A field employee is an Employee with is_labour=1, but the Field Attendance roster filters
employment_type == 'Labour' (on hrms sites). Field employees created before that stamp was set have
is_labour=1 but no employment_type, so they never appeared to be rostered. Set it for every
is_labour=1 Employee that has no employment_type. The save path is install-only, so existing sites
need this one-time backfill. Idempotent."""

import frappe

from buildsuite_core.api.field_employee import ensure_labour_employment_type


def execute():
	if not frappe.db.has_column("Employee", "is_labour") or not frappe.get_meta("Employee").has_field(
		"employment_type"
	):
		return
	targets = [
		r.name
		for r in frappe.get_all("Employee", filters={"is_labour": 1}, fields=["name", "employment_type"])
		if not r.employment_type
	]
	if not targets:
		return
	labour = ensure_labour_employment_type()
	for name in targets:
		frappe.db.set_value("Employee", name, "employment_type", labour, update_modified=False)
	frappe.db.commit()
