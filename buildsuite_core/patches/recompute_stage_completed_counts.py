# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe

from buildsuite_core.buildsuite_core.doctype.stage_planning.stage_planning import (
	recompute_stage_aggregates,
)


def execute():
	"""Recompute Stage Planning aggregates so the list's done/total chip is correct on
	existing records — covers stages whose completed_task_count was never initialised
	(template-loaded / imported rows) and applies the widened "done" rule (progress
	100 OR status Completed). Idempotent."""
	names = frappe.get_all("Stage Planning", pluck="name")
	for name in names:
		recompute_stage_aggregates(name)
	if names:
		frappe.db.commit()  # nosemgrep
