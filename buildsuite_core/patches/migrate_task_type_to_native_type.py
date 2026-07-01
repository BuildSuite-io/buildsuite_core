# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Move the scheduling type from the retired custom Select `task_type` to the
	native `type` Link (-> Task Type master), then drop the orphan field/column.

	Using native `type` lets admins add Task Types from the backend. Runs in
	post_model_sync (after the column still exists from before_migrate's field-record
	delete, before after_migrate recreates fields). Idempotent and a no-op on fresh
	installs (no `task_type` column) or sites already migrated.
	"""
	if frappe.db.has_column("Task", "task_type"):
		# Ensure a Task Type master exists for every distinct legacy value (covers the
		# core three plus any admin-set value), then bulk-copy into native `type`.
		distinct = frappe.db.sql(
			"select distinct task_type from `tabTask` where ifnull(task_type, '') != ''",
			pluck=True,
		)
		for tt in distinct:
			if not frappe.db.exists("Task Type", tt):
				frappe.get_doc({"doctype": "Task Type", "name": tt}).insert(ignore_permissions=True)

		frappe.db.sql(
			"update `tabTask` set `type` = `task_type` "
			"where ifnull(`task_type`, '') != '' and ifnull(`type`, '') = ''"
		)

		# Drop the now-unused column (its field def was removed from CUSTOM_FIELD).
		frappe.db.sql_ddl("alter table `tabTask` drop column `task_type`")

	# Remove the orphan Custom Field record so it disappears from the Task form/meta.
	frappe.db.delete("Custom Field", {"dt": "Task", "fieldname": "task_type"})
	frappe.clear_cache(doctype="Task")
