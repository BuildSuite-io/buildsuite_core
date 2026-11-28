# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Tender lifecycle and the Tenders list's figures.

A tender is a draft until it is marked submitted; it may then sit Under Evaluation before it is
Awarded or not (Rejected). The allowed moves are the controller's TENDER_TRANSITIONS. Once
submitted, a tender is frozen: re-pricing means copying it (copy_tender)."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, today

TENDER = "BuildSuite Tenders"
IN_PLAY = ("Draft", "Submitted", "Under Evaluation")


@frappe.whitelist(methods=["POST"])
def set_tender_status(name: str, status: str):
	"""Move a tender along its lifecycle (Mark submitted, Under evaluation, Awarded, Not awarded,
	Reopen)."""
	doc = frappe.get_doc(TENDER, name)
	doc.check_permission("write")
	doc.set_status(status)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist(methods=["POST"])
def copy_tender(name: str):
	"""A new draft copy of a tender, to re-price a bid that has gone out."""
	src = frappe.get_doc(TENDER, name)
	src.check_permission("read")
	if not frappe.has_permission(TENDER, "create"):
		frappe.throw(_("You are not permitted to create a tender."), frappe.PermissionError)
	copy = frappe.copy_doc(src)
	copy.title = _("{0} (revised)").format(src.title)
	copy.status = "Draft"
	copy.project = None  # the copy has not won anything yet
	copy.insert()
	return {"name": copy.name}


@frappe.whitelist()
def tender_kpis():
	"""The Tenders list's figures, over the tenders the user can read:
	- due_soon: drafts whose deadline is within a week, or already gone (overdue);
	- in_play: drafts, submitted and under evaluation;
	- emd_at_stake: earnest money on the tenders in play (it comes back on a decided bid);
	- awarded_value: bid value (incl. tax) of the tenders won;
	- win_rate: awarded out of those decided (awarded or not), None when nothing is decided."""
	rows = frappe.get_list(
		TENDER,
		fields=["name", "title", "status", "submission_deadline", "emd_amount", "bid_value"],
		limit_page_length=0,
	)
	now = getdate(today())
	horizon = getdate(add_days(now, 7))
	due_soon = sorted(
		(
			{
				"name": r.name,
				"title": r.title,
				"submission_deadline": r.submission_deadline,
				"overdue": getdate(r.submission_deadline) < now,
			}
			for r in rows
			if (r.status or "Draft") == "Draft"
			and r.submission_deadline
			and getdate(r.submission_deadline) <= horizon
		),
		key=lambda d: str(d["submission_deadline"]),
	)
	in_play = [r for r in rows if (r.status or "Draft") in IN_PLAY]
	awarded = [r for r in rows if r.status == "Awarded"]
	decided = len(awarded) + sum(1 for r in rows if r.status == "Rejected")
	return {
		"total": len(rows),
		"due_soon": due_soon,
		"in_play": len(in_play),
		"emd_at_stake": sum(flt(r.emd_amount) for r in in_play),
		"awarded_value": sum(flt(r.bid_value) for r in awarded),
		"win_rate": round(len(awarded) * 100 / decided) if decided else None,
	}
