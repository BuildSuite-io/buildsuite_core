# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Move the construction categories off the native ERPNext Project Type onto the
new Project Category master.

- Backfill Project.project_category from the legacy Project.project_type value and
  clear project_type (it goes back to native Internal/External).
- Remove the legacy category Project Types, unless something still links to them.
"""

import frappe

LEGACY_CATEGORIES = (
	"Commercial",
	"Residential",
	"Infrastructure",
	"Industrial",
	"Renovation",
	"Interior",
	"Other",
)


def execute():
	for name in LEGACY_CATEGORIES:
		if not frappe.db.exists("Project Category", name):
			frappe.get_doc(
				{"doctype": "Project Category", "category_name": name}
			).insert(ignore_permissions=True)

	# Backfill project_category from the legacy project_type, then clear project_type.
	if frappe.db.has_column("Project", "project_category"):
		for row in frappe.get_all(
			"Project",
			filters={"project_type": ("in", LEGACY_CATEGORIES)},
			fields=["name", "project_type"],
		):
			frappe.db.set_value(
				"Project",
				row.name,
				{"project_category": row.project_type, "project_type": None},
				update_modified=False,
			)

	# Drop the legacy category Project Types now nothing should reference them; skip
	# any that are still linked (e.g. an estimate template not yet migrated).
	for name in LEGACY_CATEGORIES:
		if frappe.db.exists("Project Type", name):
			try:
				frappe.delete_doc("Project Type", name, ignore_permissions=True)
			except frappe.LinkExistsError:
				pass

	frappe.db.commit()
