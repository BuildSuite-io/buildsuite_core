# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Timesheet rows made before cost codes and full-day hours: every one was made on an 8-hour day
(full_day_hours = 8), and where the row's task is linked to a BOQ line the row takes that line as its
cost code; otherwise the code stays blank. Rows are not repriced. Idempotent."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from buildsuite_core.custom_property_list.custom_field import CUSTOM_FIELD
from buildsuite_core.utils.full_day import DEFAULT_FULL_DAY_HOURS


def execute():
	# Patches run before after_migrate adds custom fields, so make the columns first.
	create_custom_fields({"Timesheet Detail": CUSTOM_FIELD["Timesheet Detail"]}, ignore_validate=True)

	frappe.db.sql(
		"UPDATE `tabTimesheet Detail` SET full_day_hours = %s WHERE full_day_hours IS NULL OR full_day_hours = 0",
		DEFAULT_FULL_DAY_HOURS,
	)

	rows = frappe.db.sql(
		"""SELECT name, task, project FROM `tabTimesheet Detail`
		WHERE IFNULL(task, '') != '' AND IFNULL(custom_cost_code_label, '') = ''""",
		as_dict=True,
	)
	for row in rows:
		line = frappe.db.sql(
			"""SELECT i.code, i.description, g.code AS group_code
			FROM `tabBOQ Item` i
			LEFT JOIN `tabBOQ Group` g ON g.name = i.boq_group
			JOIN `tabBOQ` b ON b.name = i.boq
			WHERE i.task = %s AND (%s IS NULL OR b.project = %s)
			ORDER BY b.modified DESC LIMIT 1""",
			(row.task, row.project, row.project),
			as_dict=True,
		)
		if not line:
			continue
		line = line[0]
		frappe.db.set_value(
			"Timesheet Detail",
			row.name,
			{
				"custom_cost_code_type": "Item",
				"custom_cost_code_group": line.group_code or "",
				"custom_cost_code_item": line.code,
				"custom_cost_code_label": f"{line.code} · {(line.description or '')[:50]}",
			},
			update_modified=False,
		)
