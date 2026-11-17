# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Attendance records made before full-day hours existed were all made on an 8-hour day.

Field Attendance gets full_day_hours = 8. Labour Attendance Register gets full_day_hours = 8,
regular_hours = 8 / 4 / 0 by status and source = Attendance. Overtime Attendance Register gets
full_day_hours = 8 and source = Attendance. Plain SQL updates: the rows may be submitted (and
cancelled), and nothing about them is recalculated. Idempotent - only rows still unset are touched.
"""

import frappe

from buildsuite_core.utils.full_day import DEFAULT_FULL_DAY_HOURS


def execute():
	frappe.reload_doc("buildsuite_core", "doctype", "field_attendance")
	frappe.reload_doc("buildsuite_core", "doctype", "labour_attendance_register")
	frappe.reload_doc("buildsuite_core", "doctype", "overtime_attendance_register")

	day = DEFAULT_FULL_DAY_HOURS
	unset = "(full_day_hours IS NULL OR full_day_hours = 0)"

	frappe.db.sql(f"UPDATE `tabField Attendance` SET full_day_hours = %s WHERE {unset}", day)

	frappe.db.sql(
		f"""UPDATE `tabLabour Attendance Register`
		SET full_day_hours = %(day)s,
			regular_hours = CASE status WHEN 'Full Day' THEN %(day)s WHEN 'Half Day' THEN %(day)s / 2 ELSE 0 END,
			source = 'Attendance'
		WHERE {unset}""",
		{"day": day},
	)

	frappe.db.sql(
		f"UPDATE `tabOvertime Attendance Register` SET full_day_hours = %s, source = 'Attendance' WHERE {unset}",
		day,
	)
