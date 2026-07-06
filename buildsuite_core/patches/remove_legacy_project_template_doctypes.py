# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Free the legacy category Project Types once the deprecated BuildSuite Project
Template cluster is gone.

The cluster's doctypes (BuildSuite Project Template, Stage Plan Template, Stage Plan
Task Template, Project Stage Plan Template) are removed by deleting their folders —
migrate's orphan-doctype step drops the doctypes + tables. This post_model_sync
patch then migrates any straggler projects still on the legacy project_type onto
project_category and deletes the now-unreferenced category Project Types.
"""

import frappe

_LEGACY_TYPES = ("Commercial", "Residential", "Infrastructure")


def execute():
	for name in _LEGACY_TYPES:
		if not frappe.db.exists("Project Type", name):
			continue

		# Move any project still on the legacy project_type onto project_category.
		for proj in frappe.get_all("Project", filters={"project_type": name}, pluck="name"):
			frappe.db.set_value(
				"Project",
				proj,
				{
					"project_category": frappe.db.get_value("Project", proj, "project_category")
					or name,
					"project_type": None,
				},
				update_modified=False,
			)

		try:
			frappe.delete_doc("Project Type", name, ignore_permissions=True)
		except frappe.LinkExistsError:
			pass

	frappe.db.commit()
