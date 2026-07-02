# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Rename Estimate Template.project_type -> project_category (Link to Project
Category) preserving existing tags. Runs pre_model_sync so the column is renamed
before the doctype sync reconciles it with the JSON."""

import frappe


def execute():
	if frappe.db.has_column("Estimate Template", "project_type") and not frappe.db.has_column(
		"Estimate Template", "project_category"
	):
		frappe.db.sql_ddl(
			"ALTER TABLE `tabEstimate Template` "
			"CHANGE COLUMN `project_type` `project_category` varchar(140)"
		)
