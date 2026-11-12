"""Existing Labour Attendance Register and Field Attendance rows are Regular days: Off Day is new."""

import frappe


def execute():
	for doctype in ("Labour Attendance Register", "Field Attendance"):
		if frappe.db.has_column(doctype, "day_type"):
			frappe.db.sql(f"update `tab{doctype}` set day_type = 'Regular' where ifnull(day_type, '') = ''")
