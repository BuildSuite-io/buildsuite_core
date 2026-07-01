import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from buildsuite_core.custom_property_list.custom_field import CUSTOM_FIELD
from buildsuite_core.custom_property_list.property_field import get_property_setters
from buildsuite_core.permissions.setup import setup_record_permissions
from buildsuite_core.utils.project import backfill_project_status
from buildsuite_core.utils.task import backfill_native_task_type, backfill_task_status


def after_install():
	print(_("Creating Custom Fields..."))
	create_custom_fields(CUSTOM_FIELD, ignore_validate=True)
	make_property_setters()
	seed_master_data()
	setup_record_permissions()


def after_migrate():
	print(_("Creating Custom Fields..."))
	create_custom_fields(CUSTOM_FIELD, ignore_validate=True)
	make_property_setters()
	# Backfill task_status + the native `type` on Tasks that predate the fields (idempotent).
	backfill_task_status()
	backfill_native_task_type()
	backfill_project_status()
	# Safety net for the task_type -> native `type` migration: after_migrate runs last,
	# so it reliably removes the retired custom column/record even when the patch's drop
	# (post_model_sync) races with doctype sync on the one-time transition migrate. The
	# native `type` is already populated by backfill_native_task_type() above, so this is
	# safe; it is a no-op on every subsequent migrate.
	drop_legacy_task_type_field()
	seed_master_data()
	setup_record_permissions()


def drop_legacy_task_type_field():
	"""Idempotently remove the retired custom `task_type` Select (column + record).
	Scheduling type now lives on the native `type` Link. No-op once removed."""
	if frappe.db.has_column("Task", "task_type"):
		frappe.db.sql_ddl("alter table `tabTask` drop column `task_type`")
	frappe.db.delete("Custom Field", {"dt": "Task", "fieldname": "task_type"})
	frappe.clear_cache(doctype="Task")


def seed_master_data():
	project_types = [
		"Commercial",
		"Residential",
		"Infrastructure",
		"Industrial",
		"Renovation",
		"Interior",
		"Other",
	]
	for pt in project_types:
		if not frappe.db.exists("Project Type", pt):
			frappe.get_doc({"doctype": "Project Type", "project_type": pt}).insert(ignore_permissions=True)

	# Task Type uses Prompt autoname (the type name IS the record name) and has no
	# `task_type` field — set the name directly.
	task_types = ["Activity", "Milestone", "Inspection"]
	for tt in task_types:
		if not frappe.db.exists("Task Type", tt):
			frappe.get_doc({"doctype": "Task Type", "name": tt}).insert(ignore_permissions=True)

	# Project Templates (Commercial / Residential / Infrastructure) — depend on the
	# Project Types seeded above. Idempotent (Stage-Plan-Template-exists guard).
	from buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.seed_templates import seed_all

	seed_all()


def before_migrate():
	delete_custom_fields(CUSTOM_FIELD)


def delete_custom_fields(custom_fields):
	for doctypes, fields in custom_fields.items():
		if isinstance(fields, dict):
			fields = [fields]

		if isinstance(doctypes, str):
			doctypes = (doctypes,)

		for doctype in doctypes:
			frappe.db.delete(
				"Custom Field",
				{
					"fieldname": ("in", [field["fieldname"] for field in fields]),
					"dt": doctype,
				},
			)

			frappe.clear_cache(doctype=doctype)


def make_property_setters():
	for property_setter in get_property_setters():
		frappe.make_property_setter(property_setter, validate_fields_for_doctype=False)
