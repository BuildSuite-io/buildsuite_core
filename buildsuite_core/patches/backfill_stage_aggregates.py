# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe

from buildsuite_core.buildsuite_core.doctype.stage_planning.stage_planning import (
	recompute_stage_aggregates,
)


def execute():
	"""Backfill task_count + mean_progress on existing Stage Planning records so the
	stage list shows the real nested-task count and a progress-derived status from the
	first migrate (the fields are new; without this they'd read 0 until each stage is
	next saved). Idempotent."""
	names = frappe.get_all("Stage Planning", pluck="name")
	for name in names:
		recompute_stage_aggregates(name)
	if names:
		frappe.db.commit()  # nosemgrep
