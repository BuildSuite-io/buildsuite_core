# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Authoritative BOQ totals roll-up (mirrors the prototype `_rollupBoqTotals`).

Item amounts are maintained on each BOQ Item by its own validate; the BOQ simply
sums them, then layers margin + tax and allocates both across per-Work-Package
buckets in proportion to each WP's planned share.
"""

import frappe
from frappe.utils import flt


def compute_boq_totals(doc):
	"""Recompute totals + wp_summaries IN PLACE on a BOQ doc (called from BOQ.validate)."""
	items = (
		frappe.get_all(
			"BOQ Item",
			filters={"boq": doc.name},
			fields=["planned_amount", "actual_amount", "work_package"],
		)
		if not doc.is_new()
		else []
	)
	planned = sum(flt(i.planned_amount) for i in items)
	margin = planned * flt(doc.margin_rate) / 100.0
	tax = (planned + margin) * flt(doc.tax_rate) / 100.0
	doc.planned_amount = planned
	doc.actual_amount = sum(flt(i.actual_amount) for i in items)
	doc.margin_amount = margin
	doc.tax_amount = tax
	doc.total = planned + margin + tax

	# Per-WP buckets ("" = project-level / untagged). Proportional margin + tax.
	buckets = {}
	for i in items:
		key = i.work_package or ""
		buckets[key] = buckets.get(key, 0) + flt(i.planned_amount)
	doc.set("wp_summaries", [])
	for wp, wp_planned in buckets.items():
		share = (wp_planned / planned) if planned else 0
		wp_margin = margin * share
		wp_tax = tax * share
		doc.append(
			"wp_summaries",
			{
				"work_package": wp or None,
				"planned_amount": wp_planned,
				"margin_amount": wp_margin,
				"tax_amount": wp_tax,
				"total": wp_planned + wp_margin + wp_tax,
			},
		)


def recompute_boq(boq_name):
	"""Reload + save a BOQ so its rollup refreshes after a child item changes. The
	`boq_skip_rollup` flag lets bulk API operations defer to a single recompute."""
	if frappe.flags.get("boq_skip_rollup"):
		return
	if boq_name and frappe.db.exists("BOQ", boq_name):
		frappe.get_doc("BOQ", boq_name).save(ignore_permissions=True)
