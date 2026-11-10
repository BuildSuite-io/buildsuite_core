# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the shipped approval Workflows (Stage Planning, Scope Change Order, Material Request).

They used to be fixtures, which Frappe re-imports over the site's copy on every migrate, silently
discarding an admin's edits. They are now created only when missing: a workflow that already exists
is never touched, so changes made in Desk survive. Delivering a changed definition to existing sites
is a patch's job. The definitions live in data/workflows.json."""

import json
from pathlib import Path

import frappe

_DATA = Path(__file__).parent / "data" / "workflows.json"


def seed_workflows():
	for definition in json.loads(_DATA.read_text()):
		if frappe.db.exists("Workflow", definition["workflow_name"]):
			continue
		if not frappe.db.exists("DocType", definition["document_type"]):
			continue
		frappe.get_doc(definition).insert(ignore_permissions=True)
