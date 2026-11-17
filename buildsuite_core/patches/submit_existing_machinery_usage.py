# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Machinery Usage became submittable. Logs saved before that already counted as recorded usage
(and as BOQ actuals), so mark them Submitted rather than letting them fall back to Draft and
silently drop out of the BOQ Actual. Permissions are re-applied for the new submit/cancel/amend
grants."""

import frappe

from buildsuite_core.permissions.setup import setup_equipment_permissions


def execute():
	frappe.db.sql("update `tabMachinery Usage` set docstatus = 1 where docstatus = 0")
	setup_equipment_permissions()
