import frappe
from frappe.query_builder.functions import Count, Sum
from frappe.utils import add_days, date_diff, flt, nowdate

RM_THRESHOLD_PCT = 5  # keep in sync with public/js/purchase_order.js


@frappe.whitelist()
def get_dashboard() -> dict:
	"""KPI figures for the Procurement dashboard (get_list applies user perms)."""
	return {
		"open_material_requests": _open_material_requests(),
		"on_order": _on_order(),
		"received_this_week": _received_this_week(),
		"above_estimated_rate": _above_estimated_rate(),
		"needs_action": _needs_action(),
		"recent_receipts": _recent_receipts(),
	}


def _open_material_requests() -> dict:
	"""Submitted MRs not fully ordered; value = the still-to-order portion."""
	names = frappe.get_list(
		"Material Request",
		filters={"docstatus": 1, "material_request_type": "Purchase", "per_ordered": ["<", 100]},
		pluck="name",
	)
	return {"count": len(names), "value": _pending_order_value(names)}


def _pending_order_value(mr_names: list[str]) -> float:
	"""Sum of (qty - ordered_qty) * rate over the given MRs' items."""
	if not mr_names:
		return 0.0
	mri = frappe.qb.DocType("Material Request Item")
	total = (
		frappe.qb.from_(mri)
		.select(Sum((mri.qty - mri.ordered_qty) * mri.rate))
		.where(mri.parent.isin(mr_names))
	).run()
	return flt(total[0][0]) if total else 0.0


def _on_order() -> dict:
	"""Submitted POs awaiting delivery (per_received < 100): count + full value."""
	row = frappe.get_list(
		"Purchase Order",
		filters={"docstatus": 1, "per_received": ["<", 100]},
		fields=[{"COUNT": "name", "as": "count"}, {"SUM": "grand_total", "as": "value"}],
	)[0]
	return {"count": row.count or 0, "value": flt(row.value)}


def _received_this_week() -> dict:
	"""Purchase Receipts posted in the last 7 days."""
	row = frappe.get_list(
		"Purchase Receipt",
		filters={"docstatus": 1, "posting_date": [">=", add_days(nowdate(), -7)]},
		fields=[{"COUNT": "name", "as": "count"}],
	)[0]
	return {"count": row.count or 0}


def _above_estimated_rate() -> dict:
	"""Count PO lines priced > RM_THRESHOLD_PCT above their Rate Master rate."""
	po_names = frappe.get_list("Purchase Order", filters={"docstatus": 1}, pluck="name")
	return {"count": _over_rate_line_count(po_names)}


def _over_rate_line_count(po_names: list[str]) -> int:
	"""Count lines (within the given POs) priced above the Rate Master rate."""
	if not po_names:
		return 0
	poi = frappe.qb.DocType("Purchase Order Item")
	limit = 1 + RM_THRESHOLD_PCT / 100
	return (
		frappe.qb.from_(poi)
		.select(Count(poi.name))
		.where(poi.parent.isin(po_names))
		.where(poi.custom_rate_master != "")
		.where(poi.custom_rate_master_rate > 0)
		.where(poi.rate > poi.custom_rate_master_rate * limit)
	).run()[0][0]


def _needs_action() -> dict:
	"""The four procurement to-do signals."""
	return {
		"approved_to_order": _approved_to_order(),
		"deliveries_overdue": _deliveries_overdue(),
		"partial_deliveries": _partial_deliveries(),
		"received_not_billed": _received_not_billed(),
	}


def _approved_to_order() -> dict:
	"""Submitted MRs not fully ordered, plus the oldest wait in days."""
	rows = frappe.get_list(
		"Material Request",
		filters={"docstatus": 1, "material_request_type": "Purchase", "per_ordered": ["<", 100]},
		fields=["transaction_date"],
		order_by="transaction_date asc",
	)
	oldest_days = date_diff(nowdate(), rows[0].transaction_date) if rows else 0
	return {"count": len(rows), "oldest_days": oldest_days}


def _deliveries_overdue() -> dict:
	"""Submitted POs past schedule_date and not fully received."""
	pos = frappe.get_list(
		"Purchase Order",
		filters={"docstatus": 1, "per_received": ["<", 100], "schedule_date": ["<", nowdate()]},
		fields=["name", "supplier", "schedule_date"],
		order_by="schedule_date asc",
	)
	return {"count": len(pos), "first": _overdue_first(pos[0]) if pos else None}


def _overdue_first(po: dict) -> dict:
	"""First line item (idx 1) of an overdue PO, for the sub-line."""
	item = frappe.db.get_value("Purchase Order Item", {"parent": po["name"], "idx": 1}, "item_name")
	return {
		"item": item,
		"supplier": po["supplier"],
		"required_by": po["schedule_date"],
	}


def _partial_deliveries() -> dict:
	"""Submitted POs between 1% and 99% received."""
	row = frappe.get_list(
		"Purchase Order",
		filters=[["docstatus", "=", 1], ["per_received", ">", 0], ["per_received", "<", 100]],
		fields=[{"COUNT": "name", "as": "count"}],
	)[0]
	return {"count": row.count or 0}


def _received_not_billed() -> dict:
	"""Submitted Purchase Receipts not yet fully billed."""
	row = frappe.get_list(
		"Purchase Receipt",
		filters={"docstatus": 1, "per_billed": ["<", 100]},
		fields=[{"COUNT": "name", "as": "count"}],
	)[0]
	return {"count": row.count or 0}


def _recent_receipts() -> list[dict]:
	"""The 5 latest submitted Purchase Receipts, with items and a status."""
	prs = frappe.get_list(
		"Purchase Receipt",
		filters={"docstatus": 1},
		fields=["name", "supplier", "project", "posting_date"],
		order_by="posting_date desc, creation desc",
		limit=5,
	)
	for pr in prs:
		_attach_items(pr)
	return prs


def _attach_items(pr: dict) -> None:
	"""Attach the receipt's items, item_count and a Short/Full status."""
	items = frappe.get_all(
		"Purchase Receipt Item",
		filters={"parent": pr["name"], "parenttype": "Purchase Receipt"},
		fields=["item_name", "received_qty", "rejected_qty", "uom"],
	)
	pr["items"] = [{"item": i.item_name, "qty": i.received_qty, "uom": i.uom} for i in items]
	pr["item_count"] = len(items)
	pr["status"] = _receipt_status(items)


def _receipt_status(items: list[dict]) -> str:
	"""Full (clean) / Partial (some rejected) / Short (all rejected)."""
	received = sum(flt(i.received_qty) for i in items)
	rejected = sum(flt(i.rejected_qty) for i in items)
	if rejected <= 0:
		return "Full"
	return "Short" if rejected >= received else "Partial"
