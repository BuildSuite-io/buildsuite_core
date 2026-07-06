# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the default construction Project Categories.

These replace the categories previously seeded into the native ERPNext Project
Type (which is reverted to Internal / External). Idempotent — run from
install.after_install / after_migrate.
"""

import frappe

# (category_name, sort_order)
CATEGORIES = (
	("Commercial", 1),
	("Residential", 2),
	("Infrastructure", 3),
	("Industrial", 4),
	("Renovation", 5),
	("Interior", 6),
	("Other", 7),
)


def seed_categories():
	created = []
	for name, order in CATEGORIES:
		if not frappe.db.exists("Project Category", name):
			frappe.get_doc(
				{
					"doctype": "Project Category",
					"category_name": name,
					"sort_order": order,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
			created.append(name)
	return created
