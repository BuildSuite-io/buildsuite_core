from buildsuite_core.utils.payment_terms import clear_unused_timing
from buildsuite_core.utils.project import anchor_company_to_project


def set_company(doc, method=None):
	doc.company = None
	anchor_company_to_project(doc)


def clear_milestone_timing(doc, method=None):
	clear_unused_timing(doc.get("payment_milestones") or [])


# What the SPA calls a quotation, derived from ERPNext's own fields. `status` is never
# rewritten: ERPNext reaches "Ordered" only through a Sales Order, and its daily job turns an
# offer past its validity into "Expired". "Accepted" is `accepted_on` (set by accept_quotation).
OFFER_STATUSES = ("Draft", "Sent", "Accepted", "Rejected", "Expired", "Cancelled")

# The same table as list filters, so a status filter cannot drift from its label. Every entry is
# a plain AND of ERPNext filters (no OR), so the data adapter and frappe.get_list take it as is.
OFFER_STATUS_FILTERS = {
	"Draft": {"docstatus": 0},
	"Sent": {"docstatus": 1, "status": ["in", ["Open", "Replied"]], "accepted_on": ["is", "not set"]},
	"Accepted": {"docstatus": 1, "status": ["!=", "Lost"], "accepted_on": ["is", "set"]},
	"Rejected": {"docstatus": 1, "status": "Lost"},
	"Expired": {"docstatus": 1, "status": "Expired", "accepted_on": ["is", "not set"]},
	"Cancelled": {"docstatus": 2},
}


def offer_status(docstatus, status, accepted_on=None):
	"""The SPA label for a quotation: Draft, Sent, Accepted, Rejected, Expired or Cancelled."""
	if docstatus == 0:
		return "Draft"
	if docstatus == 2:
		return "Cancelled"
	if status == "Lost":
		return "Rejected"
	if accepted_on:
		return "Accepted"
	if status == "Expired":
		return "Expired"
	return "Sent"
