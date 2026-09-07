# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Backfill employees_count on existing Field Attendance sheets.

The field is new, so every existing sheet reads 0 until it is next saved — and most are
already Submitted or Cancelled and can never be saved again. One grouped count fills
them all. Idempotent."""

import frappe


def execute():
	if not frappe.db.has_column("Field Attendance", "employees_count"):
		return

	for name, count in frappe.db.sql(
		"""
		SELECT parent, COUNT(*)
		FROM `tabField Attendance Employee`
		WHERE parenttype = 'Field Attendance'
		GROUP BY parent
		"""
	):
		frappe.db.set_value("Field Attendance", name, "employees_count", count, update_modified=False)
