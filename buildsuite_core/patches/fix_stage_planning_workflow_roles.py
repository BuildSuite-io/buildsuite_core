# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Rewire the Stage Planning Approval workflow to BuildSuite roles on existing sites.

The workflow fixture historically carried ERPNext's native `Projects User` / `Projects
Manager` roles, which no BuildSuite persona holds — so persona users could not submit,
approve, reject, revise or cancel a stage ("Not a valid Workflow Action"). The rewire
(setup_stage_planning_workflow) only ran on after_install, never on migrate, so already-
migrated sites were left on the stale roles. This heals them once; the fixture now ships
the correct roles for fresh installs and re-imports."""

import frappe

from buildsuite_core.permissions.setup import setup_stage_planning_workflow


def execute():
	if not frappe.db.exists("Workflow", "Stage Planning Approval"):
		return
	setup_stage_planning_workflow()
