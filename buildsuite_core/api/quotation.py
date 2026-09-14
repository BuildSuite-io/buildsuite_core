import frappe
from frappe import _
from frappe.utils import flt, nowdate

from buildsuite_core.api.invoice import ensure_invoice_item
from buildsuite_core.utils.project import default_company

QUOTATION = "Quotation"

PIPELINE_STATUSES = ("Open", "Replied")
WON_STATUSES = ("Ordered", "Partially Ordered")
LOST_STATUSES = ("Lost",)
UNDECIDED_STATUSES = ("Open", "Replied", "Expired")


@frappe.whitelist()
def get_summary() -> dict:
	values, counts = _values_and_counts_by_status()
	won = _sum_for(counts, WON_STATUSES)
	decided = won + _sum_for(counts, LOST_STATUSES)

	return {
		"pipeline_value": _sum_for(values, PIPELINE_STATUSES),
		"won_value": _sum_for(values, WON_STATUSES),
		"win_rate": round(won / decided * 100) if decided else None,
		"lapsed_count": _lapsed_count(),
	}


def _values_and_counts_by_status() -> tuple[dict, dict]:
	rows = frappe.get_list(
		QUOTATION,
		fields=["status", {"COUNT": "name", "as": "n"}, {"SUM": "base_grand_total", "as": "value"}],
		group_by="status",
	)
	return (
		{row.status: flt(row.value) for row in rows},
		{row.status: row.n or 0 for row in rows},
	)


def _sum_for(totals: dict, statuses: tuple) -> float:
	return sum(totals.get(status, 0) for status in statuses)


def _lapsed_count() -> int:
	rows = frappe.get_list(
		QUOTATION,
		filters=[
			["status", "in", UNDECIDED_STATUSES],
			["valid_till", "is", "set"],
			["valid_till", "<", nowdate()],
		],
		fields=[{"COUNT": "name", "as": "n"}],
	)
	return rows[0].n if rows else 0


@frappe.whitelist()
def get_quotation(name: str) -> dict:
	"""A draft in the shape the form works in — lines flattened back to what was typed."""
	doc = frappe.get_doc(QUOTATION, name)
	return {
		"party_name": doc.party_name,
		"title": doc.title,
		"customer_type": doc.customer_type,
		"project": doc.project,
		"transaction_date": doc.transaction_date,
		"valid_till": doc.valid_till,
		"tc_name": doc.tc_name,
		"terms": doc.terms,
		"internal_note": doc.internal_note,
		"items": [
			{
				"description": line.item_name,
				"uom": line.uom,
				"qty": line.qty,
				"rate": line.rate,
				"source": line.source,
				"source_code": line.source_code,
			}
			for line in doc.items
		],
	}


@frappe.whitelist()
def save_quotation(payload: str) -> dict:
	"""Create or edit a DRAFT quotation. payload: {name?, party_name, title?, customer_type?,
	project?, transaction_date?, valid_till?, tc_name?, terms?, internal_note?,
	items:[{description, uom, qty, rate, source, source_code?}]}. The keys are the doctype's
	own fieldnames, so the form needs no translation.
	"""
	data = frappe.parse_json(payload)

	customer = data.get("party_name")
	if not customer:
		frappe.throw(_("Pick the customer this quotation is for."))
	rows = data.get("items") or []
	if not rows:
		frappe.throw(_("Add at least one line."))

	doc = _draft_for_edit(data.get("name"))

	project = data.get("project") or None
	doc.company = (project and frappe.db.get_value("Project", project, "company")) or default_company()
	doc.quotation_to = "Customer"
	doc.party_name = customer
	doc.title = data.get("title") or None
	doc.customer_type = data.get("customer_type") or None
	doc.project = project
	doc.transaction_date = data.get("transaction_date") or nowdate()
	doc.valid_till = data.get("valid_till") or None
	doc.tc_name = data.get("tc_name") or None
	doc.terms = data.get("terms") or None
	doc.internal_note = data.get("internal_note") or None

	item_code = ensure_invoice_item()
	for idx, row in enumerate(rows, start=1):
		description = (row.get("description") or "").strip()
		if not description:
			frappe.throw(_("Row {0}: say what the line is for.").format(idx))
		doc.append(
			"items",
			{
				"item_code": item_code,
				"item_name": description[:140],
				"description": description,
				"uom": row.get("uom") or "Nos",
				"qty": flt(row.get("qty")) or 1,
				"rate": flt(row.get("rate")),
				"source": row.get("source") or "Manual",
				"source_code": row.get("source_code") or None,
			},
		)

	doc.save()
	return {"name": doc.name}


def _draft_for_edit(name: str | None):
	"""The quotation to write into: an existing draft with its lines cleared, else a new one."""
	if not (name and frappe.db.exists(QUOTATION, name)):
		return frappe.new_doc(QUOTATION)

	doc = frappe.get_doc(QUOTATION, name)
	if doc.docstatus != 0:
		frappe.throw(_("This quotation has been submitted — only a draft can be edited."))
	doc.set("items", [])
	return doc


# --------------------------------------------------------------------------- #
# Moving a quotation along
# --------------------------------------------------------------------------- #
def _guard_workflow():
	"""Once a site configures a workflow for Quotation, these direct docstatus endpoints
	would drift workflow_state and docstatus apart — route through the workflow instead."""
	from buildsuite_core.api.workflow import workflow_active

	if workflow_active(QUOTATION):
		frappe.throw(_("Quotation is governed by a workflow — use a workflow action."))


@frappe.whitelist()
def mark_sent(name: str) -> dict:
	"""Submit the quotation: it has gone to the customer, and its lines are now frozen."""
	_guard_workflow()
	doc = frappe.get_doc(QUOTATION, name)
	doc.submit()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def mark_accepted(name: str) -> dict:
	"""The customer said yes, so the offer becomes a confirmed Sales Order.

	ERPNext derives "Ordered" from the ordered quantity rather than a field anyone may set,
	and only a SUBMITTED order counts (sales_order.on_submit -> update_prevdoc_status). So
	the order is both how a quotation is accepted and why it has to be submitted here.
	"""
	from erpnext.selling.doctype.quotation.quotation import make_sales_order

	doc = frappe.get_doc(QUOTATION, name)
	doc.check_permission("write")  # the quotation itself is never saved here
	if doc.docstatus != 1:
		frappe.throw(_("Send the quotation to the customer before accepting it."))
	if doc.status in WON_STATUSES:
		frappe.throw(_("This quotation has already been ordered."))

	order = make_sales_order(name)
	order.insert()
	order.submit()
	return {"name": name, "sales_order": order.name}


@frappe.whitelist()
def mark_rejected(name: str, reason: str | None = None) -> dict:
	"""The customer said no. ERPNext keeps the reason on the quotation."""
	doc = frappe.get_doc(QUOTATION, name)
	doc.check_permission("write")  # declare_enquiry_lost writes with db_set, which bypasses
	if doc.docstatus != 1:
		frappe.throw(_("Send the quotation to the customer before marking it rejected."))

	doc.declare_enquiry_lost(lost_reasons_list=[], competitors=[], detailed_reason=reason)
	return {"name": name, "status": doc.status}


@frappe.whitelist()
def copy_quotation(name: str) -> dict:
	"""A fresh draft carrying the same lines, to re-price after a rejection or a lapse.

	A copy, not a revision: the original keeps the price that was actually offered.
	"""
	source = frappe.get_doc(QUOTATION, name, check_permission=True)

	# copy_doc keeps no_copy fields unless told otherwise, and set_status skips a new doc — so
	# an unguarded copy of a sent quotation reads "Open" while sitting in draft.
	copy = frappe.copy_doc(source, ignore_no_copy=False)
	copy.naming_series = source.naming_series  # no_copy, but reqd and the autoname source
	copy.title = source.title
	copy.transaction_date = nowdate()
	copy.valid_till = None
	copy.save()
	return {"name": copy.name}

