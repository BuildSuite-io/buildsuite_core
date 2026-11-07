# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Company.full_day_hours is a required field (created here first, since patches run before
after_migrate adds custom fields); give every existing Company the day that was in
force before it existed (8 hours), so labour costing is unchanged. Idempotent: only sets companies
that have no valid value yet."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from buildsuite_core.custom_property_list.custom_field import CUSTOM_FIELD
from buildsuite_core.utils.full_day import DEFAULT_FULL_DAY_HOURS, is_valid_full_day_hours


def execute():
	# Patches run before after_migrate creates custom fields, so make the column first.
	create_custom_fields({"Company": CUSTOM_FIELD["Company"]}, ignore_validate=True)
	for company, hours in frappe.get_all("Company", fields=["name", "full_day_hours"], as_list=True):
		if not is_valid_full_day_hours(hours):
			frappe.db.set_value(
				"Company", company, "full_day_hours", DEFAULT_FULL_DAY_HOURS, update_modified=False
			)
