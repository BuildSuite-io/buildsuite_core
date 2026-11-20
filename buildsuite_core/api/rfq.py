# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Request for Quotation, Supplier Quotation and their comparison, for the Vue procurement
surface. Both are ERPNext's own Buying documents, natively submittable (Draft -> Submitted ->
Cancelled, plus Amend), read and written here because each carries child tables the generic
data adapter cannot.

The flow is ERPNext's: Material Request -> Request for Quotation -> Supplier Quotation ->
Purchase Order. What this app adds on top:

* A request is for ONE project (custom parent `project`, as on Material Request); the company
  is anchored to that project, never to the user's default.
* The person and address a request goes to are copied from the Supplier's primary Contact and
  can be corrected on the request, before or after submit, with an offer to save them back.
* Email is sent on demand, one supplier at a time, from the request's page — not automatically
  on submit as ERPNext does (which would also create a portal user per supplier). `send_email`
  is therefore always stored as 0, and `send_rfq_emails` does the sending.
* A supplier's row reads Received as soon as that supplier has a submitted quotation against
  the request, whether or not it priced every line.
* `supplier_quotation_comparison` is THE comparison: one row per item asked for, one column
  per submitted quotation, the lowest rate on each row, the lowest complete supplier and the
  cheapest basket across suppliers.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate, strip_html

from buildsuite_core.api.procurement_docs import (
	_company_currency,
	_company_for,
	_default_warehouse,
	_guard_workflow,
	_mr_project,
	_po_cost_code_fields,
	_po_cost_code_obj,
	_project_name,
	_state,
)
from buildsuite_core.utils.party import primary_contact, upsert_primary_contact

RFQ = "Request for Quotation"
RFQ_SUPPLIER = "Request for Quotation Supplier"
# Most rows one list summary call answers: a list page is far smaller.
MAX_LIST_SUMMARIES = 500
SQ = "Supplier Quotation"
SQ_ITEM = "Supplier Quotation Item"
MATERIAL_REQUEST = "Material Request"
PURCHASE_ORDER = "Purchase Order"

# The Jinja format a request prints in and is emailed as (buildsuite_core.print_formats).
RFQ_PRINT_FORMAT = "BuildSuite Request for Quotation"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_email(value):
	return bool(_EMAIL_RE.match((value or "").strip()))


def _text(value):
	"""A description / message as plain text. ERPNext stores both as Text Editor (HTML); the Vue
	screens edit them as plain text, so tags a Desk edit left behind are dropped on the way out."""
	value = value or ""
	return strip_html(value).strip() if "<" in value else value.strip()


def _supplier_name(supplier):
	return frappe.db.get_value("Supplier", supplier, "supplier_name") or supplier


def _conversion_factor(item_code, uom):
	from erpnext.stock.get_item_details import get_conversion_factor

	return flt((get_conversion_factor(item_code, uom) or {}).get("conversion_factor")) or 1.0


def _line_base(row, project, default_wh):
	"""The fields a requested line and a quoted line share: the item in its unit (with the stock
	unit and conversion ERPNext needs but only fills on its own form), where it is delivered, the
	Material Request line it came from, and its cost code."""
	item_code = row.get("item_code")
	stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")
	uom = row.get("uom") or stock_uom
	return {
		"item_code": item_code,
		"qty": flt(row.get("qty")),
		"uom": uom,
		"stock_uom": stock_uom,
		"conversion_factor": _conversion_factor(item_code, uom),
		"description": (row.get("description") or "").strip() or None,
		"warehouse": default_wh,
		"material_request": row.get("material_request") or None,
		"material_request_item": row.get("material_request_item") or None,
		**_po_cost_code_fields(row.get("cost_code")),
	}


def _line_description(it):
	"""The line's own note. ERPNext fills an empty description with the Item's, which would
	only repeat the item's name under itself."""
	text = _text(it.description)
	return "" if text in (it.item_name, it.item_code) else text


# ==========================================================================
# Request for Quotation
# ==========================================================================


def _rfq_material_request(doc):
	return next((it.material_request for it in doc.items if it.material_request), None)


def _rfq_quotations(name):
	"""Every supplier quotation raised against a request that the user may read, newest first."""
	if not frappe.has_permission(SQ, "read"):
		return []
	# get_list, not get_all: a user restricted to some quotations (User Permissions on supplier,
	# project or company) sees only those.
	rows = frappe.get_list(
		SQ,
		filters={"custom_request_for_quotation": name},
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"transaction_date",
			"valid_till",
			"total",
			"grand_total",
			"status",
			"docstatus",
		],
		order_by="creation desc",
		limit_page_length=0,
	)
	for r in rows:
		r["status"] = _sq_status(r)
		r["transaction_date"] = str(r.transaction_date) if r.transaction_date else None
		r["valid_till"] = str(r.valid_till) if r.valid_till else None
	return rows


def _contact_differs(row, master):
	"""What on a request's supplier row differs from the Supplier's primary Contact, so the page
	can offer to put it back there. A blank on the request never counts."""
	contact = bool(row.custom_contact_person) and (row.custom_contact_person or "") != (
		master.get("contact_person") or ""
	)
	email = bool(row.email_id) and (row.email_id or "") != (master.get("email") or "")
	return contact or email


def _serialize_rfq(doc):
	quotations = _rfq_quotations(doc.name)
	live = {}
	for q in quotations:
		if q.docstatus != 2:
			live.setdefault(q.supplier, q)
	suppliers = []
	for s in doc.suppliers:
		master = primary_contact("Supplier", s.supplier)
		q = live.get(s.supplier)
		suppliers.append(
			{
				"name": s.name,
				"supplier": s.supplier,
				"supplier_name": s.supplier_name or _supplier_name(s.supplier),
				"contact_person": s.get("custom_contact_person") or "",
				"email_id": s.email_id or "",
				"phone": master.get("phone") or "",
				"email_sent": bool(s.email_sent),
				"email_sent_at": str(s.get("custom_email_sent_at") or "") or None,
				"quote_status": s.quote_status or "Pending",
				"differs_from_master": _contact_differs(s, master),
				"quotation": {"name": q.name, "total": flt(q.total), "status": q.status} if q else None,
			}
		)
	return {
		"name": doc.name,
		"project": doc.get("project"),
		"project_name": _project_name(doc.get("project")),
		"company": doc.company,
		"transaction_date": str(doc.transaction_date) if doc.transaction_date else None,
		"schedule_date": str(doc.schedule_date) if doc.schedule_date else None,
		"closing_date": str(doc.get("custom_closing_date") or "") or None,
		"docstatus": doc.docstatus,
		"state": _state(doc),
		"status": _state(doc),
		"amended_from": doc.get("amended_from"),
		"subject": doc.subject or "",
		"message_for_supplier": _text(doc.message_for_supplier),
		"terms": doc.terms or "",
		"tc_name": doc.tc_name or "",
		"material_request": _rfq_material_request(doc),
		"suppliers": suppliers,
		"items": [
			{
				"name": it.name,
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": _line_description(it),
				"qty": flt(it.qty),
				"uom": it.uom,
				"cost_code": _po_cost_code_obj(it),
				"material_request": it.material_request,
				"material_request_item": it.material_request_item,
			}
			for it in doc.items
		],
		"quotations": quotations,
	}


def _rfq_actions(doc):
	if doc.docstatus == 0:
		return ["edit", "submit", "delete"]
	if doc.docstatus == 1:
		return ["email", "create_quotation", "cancel"]
	return ["amend", "delete"]


@frappe.whitelist()
def get_request_for_quotation(name: str):
	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("read")
	out = _serialize_rfq(doc)
	out["actions"] = _rfq_actions(doc)
	out["email"] = _rfq_email_preview(doc)
	# Saving a corrected contact back needs the Supplier master, which not every role may edit.
	out["can_edit_supplier"] = bool(frappe.has_permission("Supplier", "write"))
	return out


@frappe.whitelist()
def get_supplier_contact(supplier: str):
	"""The contact person and email a new supplier row on a request starts with."""
	if not frappe.has_permission("Supplier", "read") and not frappe.has_permission("Supplier", "select"):
		frappe.throw(_("You are not permitted to read suppliers."), frappe.PermissionError)
	c = primary_contact("Supplier", supplier)
	return {
		"supplier": supplier,
		"supplier_name": _supplier_name(supplier),
		"contact_person": c.get("contact_person") or "",
		"email_id": c.get("email") or "",
	}


@frappe.whitelist()
def get_mr_for_rfq(material_request: str):
	"""Prefill for a request raised from a submitted Material Request: its project, the date the
	material is needed, every line (quotations are asked for the whole request, ordered or not)
	and a subject to start from."""
	doc = frappe.get_doc(MATERIAL_REQUEST, material_request)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Submit the material request before asking for quotations."))
	project = _mr_project(doc)
	lines = [
		{
			"item_code": it.item_code,
			"item_name": it.item_name,
			"description": _line_description(it),
			"qty": flt(it.qty),
			"uom": it.uom,
			"cost_code": _po_cost_code_obj(it),
			"material_request": doc.name,
			"material_request_item": it.name,
		}
		for it in doc.items
	]
	names = [l["item_name"] or l["item_code"] for l in lines]
	subject = _("Request for Quotation: {0}").format(", ".join(names[:2]))
	if len(names) > 2:
		subject += " " + _("and more")
	if project:
		subject += ", " + (_project_name(project) or project)
	return {
		"material_request": doc.name,
		"project": project,
		"project_name": _project_name(project),
		"schedule_date": str(doc.schedule_date) if doc.schedule_date else None,
		"subject": subject,
		"lines": lines,
	}


@frappe.whitelist()
def save_request_for_quotation(
	name: str | None = None,
	project: str | None = None,
	transaction_date: str | None = None,
	schedule_date: str | None = None,
	closing_date: str | None = None,
	subject: str | None = None,
	message_for_supplier: str | None = None,
	terms: str | None = None,
	tc_name: str | None = None,
	suppliers: str | None = None,
	items: str | None = None,
):
	"""Create / update a draft Request for Quotation. One project for the whole request, stamped
	on every line and used to anchor the company. A submitted request is cancelled, not edited."""
	suppliers = frappe.parse_json(suppliers) or []
	items = frappe.parse_json(items) or []
	if not project:
		frappe.throw(_("Pick a project for the request."))
	subject = (subject or "").strip()
	if not subject:
		frappe.throw(_("Give the request a subject: it is the email subject too."))

	if name and frappe.db.exists(RFQ, name):
		doc = frappe.get_doc(RFQ, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft request can be edited."))
	else:
		doc = frappe.new_doc(RFQ)

	doc.company = _company_for(project)
	doc.project = project
	doc.transaction_date = transaction_date or doc.transaction_date or nowdate()
	doc.schedule_date = schedule_date or None
	doc.custom_closing_date = closing_date or None
	doc.subject = subject
	doc.message_for_supplier = message_for_supplier or ""
	if terms is not None:
		doc.terms = terms
		doc.tc_name = tc_name or None

	doc.set("suppliers", [])
	seen = set()
	for row in suppliers:
		supplier = row.get("supplier")
		if not supplier or supplier in seen:
			continue
		seen.add(supplier)
		email = (row.get("email_id") or "").strip()
		if email and not _is_email(email):
			frappe.throw(_("{0}: that email address does not look right.").format(_supplier_name(supplier)))
		doc.append(
			"suppliers",
			{
				"supplier": supplier,
				"contact": primary_contact("Supplier", supplier).get("_name"),
				"custom_contact_person": (row.get("contact_person") or "").strip(),
				"email_id": email,
				# Never ERPNext's send-on-submit (see the module note); email goes on demand.
				"send_email": 0,
			},
		)
	if not doc.get("suppliers"):
		frappe.throw(_("Add at least one supplier to ask."))

	default_wh = _default_warehouse(doc.company, project)
	doc.set("items", [])
	for row in items:
		if not row.get("item_code") or flt(row.get("qty")) <= 0:
			continue
		doc.append(
			"items",
			{
				**_line_base(row, project, default_wh),
				"schedule_date": schedule_date or doc.transaction_date,
				"project_name": project,
			},
		)
	if not doc.get("items"):
		frappe.throw(_("Add at least one item with a quantity."))

	doc.save()
	return _serialize_rfq(doc)


@frappe.whitelist()
def submit_request_for_quotation(name: str):
	_guard_workflow(RFQ, _("Request for Quotation"))
	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("submit")
	# A request saved from Desk may carry ERPNext's send-on-submit; this surface sends on demand.
	for row in doc.suppliers:
		row.send_email = 0
	doc.submit()
	return get_request_for_quotation(name)


@frappe.whitelist()
def cancel_request_for_quotation(name: str):
	_guard_workflow(RFQ, _("Request for Quotation"))
	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("cancel")
	live = frappe.db.get_value(SQ, {"custom_request_for_quotation": name, "docstatus": 1}, "name")
	if live:
		frappe.throw(_("Supplier quotation {0} answers this request. Cancel it first.").format(live))
	doc.cancel()
	return get_request_for_quotation(name)


@frappe.whitelist()
def amend_request_for_quotation(name: str):
	src = frappe.get_doc(RFQ, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled request can be amended."))
	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	for row in amended.suppliers:
		row.send_email = 0
		row.email_sent = 0
		row.custom_email_sent_at = None
		row.quote_status = "Pending"
	amended.insert()
	return get_request_for_quotation(amended.name)


@frappe.whitelist()
def delete_request_for_quotation(name: str):
	doc = frappe.get_doc(RFQ, name)
	if doc.docstatus == 1:
		frappe.throw(_("A submitted request is cancelled first."))
	if frappe.db.exists(SQ, {"custom_request_for_quotation": name}):
		frappe.throw(_("Supplier quotations refer to this request."))
	frappe.delete_doc(RFQ, name)
	return {"ok": True}


def _supplier_row(doc, supplier):
	row = next((s for s in doc.suppliers if s.supplier == supplier), None)
	if not row:
		frappe.throw(_("{0} is not on this request.").format(_supplier_name(supplier)))
	return row


@frappe.whitelist()
def set_rfq_supplier_contact(
	name: str, supplier: str, contact_person: str | None = None, email_id: str | None = None
):
	"""Correct the person or address a request goes to. Allowed until the request is cancelled:
	a wrong address is usually found when the mail is about to go, after submit."""
	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("write")
	if doc.docstatus == 2:
		frappe.throw(_("This request is cancelled."))
	row = _supplier_row(doc, supplier)
	values = {}
	if contact_person is not None:
		values["custom_contact_person"] = contact_person.strip()
	if email_id is not None:
		email_id = email_id.strip()
		if email_id and not _is_email(email_id):
			frappe.throw(_("That email address does not look right."))
		values["email_id"] = email_id
	if values:
		frappe.db.set_value(RFQ_SUPPLIER, row.name, values)
		doc.notify_update()
	return get_request_for_quotation(name)


@frappe.whitelist()
def save_rfq_contact_to_supplier(name: str, supplier: str):
	"""Put the contact person and email on a request's supplier row back on the Supplier's
	primary Contact, so the next request starts from them."""
	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("read")
	if not frappe.has_permission("Supplier", "write"):
		frappe.throw(_("Your role cannot edit the Supplier master."), frappe.PermissionError)
	row = _supplier_row(doc, supplier)
	upsert_primary_contact(
		"Supplier",
		supplier,
		_supplier_name(supplier),
		row.get("custom_contact_person"),
		None,
		row.email_id,
	)
	contact = primary_contact("Supplier", supplier).get("_name")
	if contact and row.contact != contact:
		frappe.db.set_value(RFQ_SUPPLIER, row.name, "contact", contact)
	return get_request_for_quotation(name)


# --------------------------------------------------------------------------
# Email and print — one copy per supplier
# --------------------------------------------------------------------------


def _rfq_email(doc, row):
	"""The email one supplier gets: who, the subject, and the body. The greeting names the
	contact the copy is addressed to; a message that opens with its own salutation keeps it only
	when no contact is named."""
	body = _text(doc.message_for_supplier)
	contact = (row.get("custom_contact_person") or "").strip() if row else ""
	if contact:
		body = re.sub(r"^dear[^\n]*\n+", "", body, flags=re.IGNORECASE)
		greeting = _("Dear {0},").format(contact)
	elif re.match(r"^dear", body, flags=re.IGNORECASE):
		greeting = ""
	else:
		greeting = _("Dear Sir / Madam,")
	company = frappe.db.get_value("Company", doc.company, "company_name") or doc.company or ""
	parts = [
		greeting,
		body,
		_("The request is attached ({0}).").format(doc.name),
		_("Regards,") + "\n" + company,
	]
	return {
		"to": (row.email_id or "") if row else "",
		"subject": doc.subject or _("Request for Quotation {0}").format(doc.name),
		"body": "\n\n".join(p for p in parts if p).strip(),
	}


def _rfq_email_preview(doc):
	"""Each supplier's email, keyed by supplier, for the page's preview before sending."""
	return {s.supplier: _rfq_email(doc, s) for s in doc.suppliers}


def _rfq_letterhead(doc):
	from buildsuite_core.api.printing import _letter_head_for_company

	return _letter_head_for_company(RFQ, doc.name)


def _rfq_print_format():
	"""The format a request prints in: the doctype's default (an admin's Desk choice wins), else
	ours, else whatever Frappe falls back to."""
	default = frappe.get_meta(RFQ).default_print_format
	if default and frappe.db.exists("Print Format", default):
		return default
	return RFQ_PRINT_FORMAT if frappe.db.exists("Print Format", RFQ_PRINT_FORMAT) else None


@frappe.whitelist()
def get_rfq_print_html(name: str, supplier: str | None = None):
	"""``{html, style, print_format}`` for a request's print view, addressed to one of its
	suppliers (the first when none is named). The same document is what the email attaches."""
	from frappe.www.printview import get_html_and_style

	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("read")
	if supplier:
		_supplier_row(doc, supplier)
		# ERPNext's own field for "the supplier this copy is for" (Tools > Download PDF).
		doc.vendor = supplier
	print_format = _rfq_print_format()
	result = get_html_and_style(
		doc=doc.as_json(),
		print_format=print_format,
		letterhead=_rfq_letterhead(doc),
		trigger_print=False,
	)
	return {
		"html": result.get("html"),
		"style": result.get("style"),
		"print_format": print_format or "Standard",
	}


def _rfq_attachment(doc, supplier):
	"""The request as a file for one supplier's email: a PDF, or the same document as HTML where
	this server cannot make PDFs (no PDF engine installed) so the send still goes."""
	doc.vendor = supplier
	kwargs = {"print_format": _rfq_print_format(), "doc": doc, "letterhead": _rfq_letterhead(doc)}
	try:
		return {
			"fname": f"{doc.name}.pdf",
			"fcontent": frappe.get_print(RFQ, doc.name, as_pdf=True, **kwargs),
		}
	except Exception:
		frappe.clear_last_message()
		frappe.log_error(title="Request for Quotation PDF", message=frappe.get_traceback())
		return {"fname": f"{doc.name}.html", "fcontent": frappe.get_print(RFQ, doc.name, **kwargs)}


@frappe.whitelist()
def send_rfq_emails(name: str, suppliers: str | None = None):
	"""Email a submitted request to some (or all) of its suppliers, each with its own copy
	attached. Records when each one was sent; a supplier with no valid address is skipped and
	named. Returns ``{sent, skipped, doc}``."""
	from frappe.core.doctype.communication.email import make

	doc = frappe.get_doc(RFQ, name)
	doc.check_permission("write")
	if doc.docstatus != 1:
		frappe.throw(_("Submit the request before sending it."))
	only = frappe.parse_json(suppliers) if suppliers else None

	sent, skipped = [], []
	for row in doc.suppliers:
		if only is not None and row.supplier not in only:
			continue
		label = row.supplier_name or _supplier_name(row.supplier)
		if not _is_email(row.email_id):
			skipped.append(label)
			continue
		mail = _rfq_email(doc, row)
		try:
			make(
				doctype=RFQ,
				name=doc.name,
				subject=mail["subject"],
				content=frappe.utils.escape_html(mail["body"]).replace("\n", "<br>"),
				recipients=[row.email_id.strip()],
				attachments=[_rfq_attachment(doc, row.supplier)],
				send_email=True,
			)
		except frappe.OutgoingEmailError:
			frappe.clear_last_message()
			frappe.throw(
				_(
					"No outgoing email account is set up, so nothing was sent. Ask an administrator to add one, then send again."
				),
				title=_("Email is not set up"),
			)
		frappe.db.set_value(RFQ_SUPPLIER, row.name, {"email_sent": 1, "custom_email_sent_at": now_datetime()})
		sent.append(label)

	if not sent and not skipped:
		frappe.throw(_("Pick at least one supplier to send to."))
	if not sent:
		frappe.throw(_("None of those suppliers has an email address."))
	doc.notify_update()
	return {"sent": sent, "skipped": skipped, "doc": get_request_for_quotation(name)}


@frappe.whitelist()
def rfq_list_summaries(names: str | list | None = None):
	"""Per request in `names` (the rows the list is showing), what its row shows beyond the
	parent's own fields: the suppliers asked, how many have quoted, the number of items and the
	Material Request it came from. Only the requests asked for are read, and only those the user
	may read, so the cost follows the page, not the whole history."""
	names = frappe.parse_json(names) if isinstance(names, str) else names
	names = [n for n in (names or []) if isinstance(n, str)][:MAX_LIST_SUMMARIES]
	if not names:
		return {}
	names = frappe.get_list(RFQ, filters={"name": ["in", names]}, pluck="name", limit_page_length=0)
	if not names:
		return {}
	out = {n: {"suppliers": [], "received": 0, "items": 0, "material_request": None} for n in names}
	for s in frappe.get_all(
		RFQ_SUPPLIER,
		filters={"parent": ["in", names], "parenttype": RFQ},
		fields=["parent", "supplier", "supplier_name", "quote_status"],
		order_by="parent, idx",
	):
		row = out[s.parent]
		row["suppliers"].append(s.supplier_name or _supplier_name(s.supplier))
		if s.quote_status == "Received":
			row["received"] += 1
	for it in frappe.get_all(
		"Request for Quotation Item",
		filters={"parent": ["in", names], "parenttype": RFQ},
		fields=["parent", "material_request"],
	):
		row = out[it.parent]
		row["items"] += 1
		row["material_request"] = row["material_request"] or it.material_request
	return out


def rfqs_for_material_request(material_request):
	"""The live (not cancelled) requests for quotation raised from a Material Request, for its
	page's banner. Empty for a user who may not read requests for quotation."""
	if not frappe.has_permission(RFQ, "read"):
		return []
	parents = frappe.get_all(
		"Request for Quotation Item",
		filters={"material_request": material_request, "parenttype": RFQ, "docstatus": ["!=", 2]},
		pluck="parent",
		distinct=True,
	)
	if not parents:
		return []
	rows = frappe.get_list(
		RFQ,
		filters={"name": ["in", parents]},
		fields=["name", "docstatus"],
		order_by="creation asc",
	)
	return [{"name": r.name, "status": _state(r)} for r in rows]


# ==========================================================================
# Supplier Quotation
# ==========================================================================


def _sq_status(doc):
	"""ERPNext's status, with Expired read off the date: a daily job stamps it, but a quotation
	that ran out this morning should already say so."""
	status = doc.get("status") or _state(doc)
	if doc.docstatus == 1 and status == "Submitted" and doc.get("valid_till"):
		if getdate(doc.valid_till) < getdate(nowdate()):
			return "Expired"
	return status


def _sq_ordered_stock_qty(item_names):
	"""Stock quantity already ordered against each Supplier Quotation line, from the Purchase Order
	lines raised from it (drafts count, so a second order can't be started twice over the same
	quote; cancelled orders don't). ERPNext keeps no ordered quantity on Supplier Quotation Item
	and no Ordered status on Supplier Quotation, so it is read off the orders themselves."""
	if not item_names:
		return {}
	rows = frappe.get_all(
		"Purchase Order Item",
		filters={
			"supplier_quotation_item": ["in", list(item_names)],
			"parenttype": PURCHASE_ORDER,
			"docstatus": ["<", 2],
		},
		fields=["supplier_quotation_item", {"SUM": "stock_qty", "as": "stock_qty"}],
		group_by="supplier_quotation_item",
	)
	return {r.supplier_quotation_item: flt(r.stock_qty) for r in rows}


def _sq_remaining(doc):
	"""Per priced line: (line, quantity still to order in the quotation's unit)."""
	priced = [it for it in doc.items if flt(it.rate) > 0]
	ordered = _sq_ordered_stock_qty([it.name for it in priced])
	return [
		(it, max(flt(it.qty) - ordered.get(it.name, 0) / (flt(it.conversion_factor) or 1), 0))
		for it in priced
	]


def _sq_purchase_orders(name):
	if not frappe.has_permission(PURCHASE_ORDER, "read"):
		return []
	parents = frappe.get_all(
		"Purchase Order Item",
		filters={"supplier_quotation": name, "parenttype": PURCHASE_ORDER},
		pluck="parent",
		distinct=True,
	)
	if not parents:
		return []
	return frappe.get_list(
		PURCHASE_ORDER,
		filters={"name": ["in", parents]},
		fields=["name", "status", "grand_total", "docstatus"],
		order_by="creation asc",
	)


def _serialize_sq(doc):
	remaining = {it.name: left for it, left in _sq_remaining(doc)} if doc.docstatus == 1 else {}
	return {
		"name": doc.name,
		"supplier": doc.supplier,
		"supplier_name": doc.supplier_name or _supplier_name(doc.supplier),
		"project": doc.project,
		"project_name": _project_name(doc.project),
		"company": doc.company,
		"request_for_quotation": doc.get("custom_request_for_quotation"),
		"transaction_date": str(doc.transaction_date) if doc.transaction_date else None,
		"valid_till": str(doc.valid_till) if doc.valid_till else None,
		"quotation_number": doc.quotation_number or "",
		"payment_terms": doc.get("custom_payment_terms") or "",
		"notes": doc.get("custom_supplier_notes") or "",
		"currency": doc.currency,
		"total": flt(doc.total),
		"total_taxes_and_charges": flt(doc.total_taxes_and_charges),
		"grand_total": flt(doc.grand_total),
		"taxes_and_charges": doc.taxes_and_charges or "",
		"taxes": [
			{
				"description": t.description or t.account_head,
				"account_head": t.account_head,
				"rate": flt(t.rate),
				"tax_amount": flt(t.tax_amount),
			}
			for t in doc.taxes
		],
		"docstatus": doc.docstatus,
		"state": _state(doc),
		"status": _sq_status(doc),
		# Something the supplier priced is still to be ordered (drives "Create purchase order").
		"to_order": any(left > 0 for left in remaining.values()),
		"amended_from": doc.get("amended_from"),
		"items": [
			{
				"name": it.name,
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": _line_description(it),
				"qty": flt(it.qty),
				"uom": it.uom,
				"rate": flt(it.rate),
				"amount": flt(it.amount),
				"lead_time_days": it.lead_time_days if it.lead_time_days else None,
				# Quantity already on purchase orders, in the quotation's unit (submitted only).
				"ordered_qty": flt(it.qty) - remaining[it.name] if it.name in remaining else 0,
				"cost_code": _po_cost_code_obj(it),
				"request_for_quotation": it.request_for_quotation,
				"request_for_quotation_item": it.request_for_quotation_item,
				"material_request": it.material_request,
				"material_request_item": it.material_request_item,
			}
			for it in doc.items
		],
	}


def _sq_actions(doc):
	if doc.docstatus == 0:
		return ["edit", "submit", "delete"]
	if doc.docstatus == 1:
		return ["create_po", "cancel"]
	return ["amend", "delete"]


@frappe.whitelist()
def get_supplier_quotation(name: str):
	doc = frappe.get_doc(SQ, name)
	doc.check_permission("read")
	out = _serialize_sq(doc)
	out["actions"] = _sq_actions(doc)
	out["purchase_orders"] = _sq_purchase_orders(name)
	return out


@frappe.whitelist()
def get_rfq_for_sq(request_for_quotation: str):
	"""Prefill for a quotation that answers a request: its project, the suppliers it went to
	(with whether each has quoted) and its lines, waiting for the supplier's rates."""
	doc = frappe.get_doc(RFQ, request_for_quotation)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Quotations are recorded against a submitted request."))
	return {
		"request_for_quotation": doc.name,
		"subject": doc.subject or "",
		"project": doc.get("project"),
		"project_name": _project_name(doc.get("project")),
		"suppliers": [
			{
				"supplier": s.supplier,
				"supplier_name": s.supplier_name or _supplier_name(s.supplier),
				"quote_status": s.quote_status or "Pending",
			}
			for s in doc.suppliers
		],
		"lines": [
			{
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": _line_description(it),
				"qty": flt(it.qty),
				"uom": it.uom,
				"rate": None,
				"lead_time_days": None,
				"cost_code": _po_cost_code_obj(it),
				"request_for_quotation": doc.name,
				"request_for_quotation_item": it.name,
				"material_request": it.material_request,
				"material_request_item": it.material_request_item,
			}
			for it in doc.items
		],
	}


def _apply_sq_taxes(doc, template):
	"""The quotation's Taxes and Charges: the rows of the chosen Purchase Taxes and Charges
	Template, each a rate on the net (amounts are worked out by the controller)."""
	from buildsuite_core.api.supplier_bill import get_tax_template_rows

	doc.taxes_and_charges = template or None
	doc.set("taxes", [])
	if not template:
		return
	if frappe.db.get_value("Purchase Taxes and Charges Template", template, "company") != doc.company:
		frappe.throw(_("Tax template {0} does not belong to company {1}.").format(template, doc.company))
	for t in get_tax_template_rows(template):
		if not t.get("account_head"):
			continue
		doc.append(
			"taxes",
			{
				"charge_type": t.get("charge_type") or "On Net Total",
				"account_head": t.get("account_head"),
				"description": t.get("description") or t.get("account_head"),
				"rate": flt(t.get("rate")),
				"category": "Total",
				"add_deduct_tax": "Add",
			},
		)


@frappe.whitelist()
def save_supplier_quotation(
	name: str | None = None,
	supplier: str | None = None,
	project: str | None = None,
	request_for_quotation: str | None = None,
	transaction_date: str | None = None,
	valid_till: str | None = None,
	quotation_number: str | None = None,
	payment_terms: str | None = None,
	notes: str | None = None,
	taxes_and_charges: str | None = None,
	items: str | None = None,
):
	"""Create / update a draft Supplier Quotation: what one supplier answered — a rate for each
	item (none on a line it did not quote), its lead time, taxes and validity. Against a request
	the project is the request's and the supplier must be one it was sent to."""
	items = frappe.parse_json(items) or []
	if not supplier:
		frappe.throw(_("Pick a supplier."))

	if name and frappe.db.exists(SQ, name):
		doc = frappe.get_doc(SQ, name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("Only a draft quotation can be edited."))
		# The request a quotation answers is fixed once it is saved.
		request_for_quotation = doc.get("custom_request_for_quotation")
	else:
		doc = frappe.new_doc(SQ)

	if request_for_quotation:
		rfq = frappe.get_doc(RFQ, request_for_quotation)
		if rfq.docstatus != 1:
			frappe.throw(_("Quotations are recorded against a submitted request."))
		if not any(s.supplier == supplier for s in rfq.suppliers):
			frappe.throw(_("{0} was not asked to quote on {1}.").format(_supplier_name(supplier), rfq.name))
		project = rfq.get("project") or project
	if not project:
		frappe.throw(_("Pick a project."))

	company = _company_for(project)
	doc.supplier = supplier
	doc.company = company
	doc.currency = _company_currency(company)
	doc.conversion_rate = 1
	doc.project = project
	doc.custom_request_for_quotation = request_for_quotation or None
	doc.transaction_date = transaction_date or doc.transaction_date or nowdate()
	doc.valid_till = valid_till or None
	doc.quotation_number = (quotation_number or "").strip() or None
	doc.custom_payment_terms = (payment_terms or "").strip()
	doc.custom_supplier_notes = (notes or "").strip()

	default_wh = _default_warehouse(company, project)
	doc.set("items", [])
	for row in items:
		if not row.get("item_code") or flt(row.get("qty")) <= 0:
			continue
		lead = row.get("lead_time_days")
		doc.append(
			"items",
			{
				**_line_base(row, project, default_wh),
				"rate": flt(row.get("rate")),
				# The supplier's rate IS the list rate here. Left empty, ERPNext fills it from the
				# item's price list and then prices a line the supplier did not quote from it.
				"price_list_rate": flt(row.get("rate")),
				"discount_percentage": 0,
				"lead_time_days": int(flt(lead)) if lead not in (None, "") else 0,
				"project": project,
				# The line link is what marks the request answered and feeds the comparison.
				"request_for_quotation": request_for_quotation or None,
				"request_for_quotation_item": (
					row.get("request_for_quotation_item") if request_for_quotation else None
				),
			},
		)
	if not doc.get("items"):
		frappe.throw(_("Add at least one item with a quantity."))

	_apply_sq_taxes(doc, taxes_and_charges)
	doc.save()
	return _serialize_sq(doc)


def _sync_rfq_quote_status(request_for_quotation):
	"""A supplier's row on the request reads Received while that supplier has a submitted
	quotation against it, Pending otherwise. ERPNext sets Received only when every line was
	quoted; here a part quotation is still an answer, and the comparison shows what is missing."""
	if not request_for_quotation:
		return
	answered = set(
		frappe.get_all(
			SQ,
			filters={"custom_request_for_quotation": request_for_quotation, "docstatus": 1},
			pluck="supplier",
		)
	)
	for row in frappe.get_all(
		RFQ_SUPPLIER,
		filters={"parent": request_for_quotation, "parenttype": RFQ},
		fields=["name", "supplier", "quote_status"],
	):
		status = "Received" if row.supplier in answered else "Pending"
		if row.quote_status != status:
			frappe.db.set_value(RFQ_SUPPLIER, row.name, "quote_status", status)


@frappe.whitelist()
def submit_supplier_quotation(name: str):
	_guard_workflow(SQ, _("Supplier Quotation"))
	doc = frappe.get_doc(SQ, name)
	doc.check_permission("submit")
	if not any(flt(it.rate) > 0 for it in doc.items):
		frappe.throw(_("Enter a rate on at least one item."))
	rfq = doc.get("custom_request_for_quotation")
	if rfq:
		twin = frappe.db.get_value(
			SQ,
			{
				"custom_request_for_quotation": rfq,
				"supplier": doc.supplier,
				"docstatus": 1,
				"name": ["!=", name],
			},
			"name",
		)
		if twin:
			frappe.throw(
				_("{0} is already this supplier's quotation for the request. Cancel it first.").format(twin)
			)
	doc.submit()
	_sync_rfq_quote_status(rfq)
	return get_supplier_quotation(name)


@frappe.whitelist()
def cancel_supplier_quotation(name: str):
	_guard_workflow(SQ, _("Supplier Quotation"))
	doc = frappe.get_doc(SQ, name)
	doc.check_permission("cancel")
	po = frappe.db.get_value(
		"Purchase Order Item",
		{"supplier_quotation": name, "parenttype": PURCHASE_ORDER, "docstatus": ["!=", 2]},
		"parent",
	)
	if po:
		frappe.throw(_("Purchase order {0} was raised from this quotation. Cancel it first.").format(po))
	doc.cancel()
	_sync_rfq_quote_status(doc.get("custom_request_for_quotation"))
	return get_supplier_quotation(name)


@frappe.whitelist()
def amend_supplier_quotation(name: str):
	src = frappe.get_doc(SQ, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled quotation can be amended."))
	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	# no_copy drops the parent link on a copy; an amendment answers the same request.
	amended.custom_request_for_quotation = src.get("custom_request_for_quotation")
	amended.insert()
	return get_supplier_quotation(amended.name)


@frappe.whitelist()
def delete_supplier_quotation(name: str):
	doc = frappe.get_doc(SQ, name)
	if doc.docstatus == 1:
		frappe.throw(_("A submitted quotation is cancelled first."))
	frappe.delete_doc(SQ, name)
	return {"ok": True}


@frappe.whitelist()
def get_sq_for_po(supplier_quotation: str):
	"""Prefill for a Purchase Order raised from a submitted quotation: the supplier, the lines the
	supplier priced (quantity net of what is already ordered) at the quoted rates, the taxes
	quoted, and the date the request needed the material by."""
	doc = frappe.get_doc(SQ, supplier_quotation)
	doc.check_permission("read")
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted quotation can be ordered from."))
	rfq = doc.get("custom_request_for_quotation")
	schedule_date = frappe.db.get_value(RFQ, rfq, "schedule_date") if rfq else None
	lines = []
	for it, remaining in _sq_remaining(doc):
		if remaining <= 0:
			continue
		lines.append(
			{
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": _line_description(it),
				"qty": remaining,
				"uom": it.uom,
				"rate": flt(it.rate),
				"cost_code": _po_cost_code_obj(it),
				"material_request": it.material_request,
				"material_request_item": it.material_request_item,
				"supplier_quotation": doc.name,
				"supplier_quotation_item": it.name,
			}
		)
	return {
		"supplier_quotation": doc.name,
		"status": _sq_status(doc),
		"valid_till": str(doc.valid_till) if doc.valid_till else None,
		"supplier": doc.supplier,
		"supplier_name": doc.supplier_name,
		"project": doc.project,
		"project_name": _project_name(doc.project),
		"request_for_quotation": rfq,
		"schedule_date": str(schedule_date) if schedule_date else None,
		"taxes_and_charges": doc.taxes_and_charges or "",
		"total_taxes_and_charges": flt(doc.total_taxes_and_charges),
		"lines": lines,
	}


def copy_sq_taxes_to_po(po, supplier_quotation):
	"""A new order raised from a quotation starts with the taxes the supplier quoted, as
	ERPNext's own Supplier Quotation -> Purchase Order mapping copies them."""
	sq = frappe.db.get_value(
		SQ, supplier_quotation, ["docstatus", "company", "taxes_and_charges"], as_dict=True
	)
	if not sq or sq.docstatus != 1 or sq.company != po.company:
		return
	po.taxes_and_charges = sq.taxes_and_charges or None
	po.set("taxes", [])
	for t in frappe.get_all(
		"Purchase Taxes and Charges",
		filters={"parent": supplier_quotation, "parenttype": SQ},
		fields=["charge_type", "account_head", "description", "rate", "category", "add_deduct_tax"],
		order_by="idx",
	):
		po.append("taxes", dict(t))


# ==========================================================================
# Supplier Quotation Comparison
# ==========================================================================


@frappe.whitelist()
def comparison_requests():
	"""The requests the comparison can be run for (anything past Draft), newest first, each with
	how many suppliers have a submitted quotation against it."""
	if not frappe.has_permission(SQ, "read"):
		frappe.throw(_("You are not permitted to read supplier quotations."), frappe.PermissionError)
	rows = frappe.get_list(
		RFQ,
		filters={"docstatus": ["!=", 0]},
		fields=["name", "subject", "transaction_date", "project", "docstatus"],
		order_by="transaction_date desc, creation desc",
		limit_page_length=0,
	)
	if not rows:
		return []
	quoted = {}
	for q in frappe.get_list(  # only the quotations this user may read are counted
		SQ,
		filters={"custom_request_for_quotation": ["in", [r.name for r in rows]], "docstatus": 1},
		fields=["custom_request_for_quotation as rfq"],
		limit_page_length=0,
	):
		quoted[q.rfq] = quoted.get(q.rfq, 0) + 1
	return [
		{
			"name": r.name,
			"subject": r.subject or "",
			"transaction_date": str(r.transaction_date) if r.transaction_date else None,
			"project": r.project,
			"status": _state(r),
			"quoted": quoted.get(r.name, 0),
		}
		for r in rows
	]


@frappe.whitelist()
def supplier_quotation_comparison(request_for_quotation: str):
	"""What each supplier quoted for a request, item by item.

	One row per item asked for; one column per SUBMITTED quotation, in the order the suppliers
	are listed on the request. A line with no rate reads as not quoted. `low` marks the lowest
	rate on a row; `best_quotation` is the lowest supplier that priced every item; `basket` is
	what the request would cost if each item were bought from whoever quoted it lowest, which is
	usually less than any one supplier's total."""
	rfq = frappe.get_doc(RFQ, request_for_quotation)
	rfq.check_permission("read")
	if not frappe.has_permission(SQ, "read"):
		frappe.throw(_("You are not permitted to read supplier quotations."), frappe.PermissionError)

	order = {s.supplier: i for i, s in enumerate(rfq.suppliers)}
	# Only the quotations this user may read; their lines are then read for those alone.
	quotes = frappe.get_list(
		SQ,
		filters={"custom_request_for_quotation": rfq.name, "docstatus": 1},
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"transaction_date",
			"valid_till",
			"total_taxes_and_charges",
			"total",
			"status",
			"docstatus",
			"custom_payment_terms as payment_terms",
		],
		limit_page_length=0,
	)
	quotes.sort(key=lambda q: (order.get(q.supplier, 999), q.name))

	lines = {}
	if quotes:
		for l in frappe.get_all(
			SQ_ITEM,
			filters={"parent": ["in", [q.name for q in quotes]], "parenttype": SQ},
			fields=["parent", "item_code", "rate", "lead_time_days", "request_for_quotation_item"],
			order_by="parent, idx",
		):
			lines.setdefault(l.parent, []).append(l)

	def quoted_line(quote, item):
		mine = lines.get(quote.name, [])
		return next((l for l in mine if l.request_for_quotation_item == item.name), None) or next(
			(l for l in mine if not l.request_for_quotation_item and l.item_code == item.item_code), None
		)

	rows = []
	for it in rfq.items:
		qty = flt(it.qty)
		cells = []
		for q in quotes:
			l = quoted_line(q, it)
			if l and flt(l.rate) > 0:
				cells.append(
					{
						"quotation": q.name,
						"rate": flt(l.rate),
						"amount": flt(flt(l.rate) * qty, 2),
						"lead_time_days": l.lead_time_days or None,
					}
				)
			else:
				cells.append(None)
		rates = [c["rate"] for c in cells if c]
		low = min(rates) if rates else None
		rows.append(
			{
				"name": it.name,
				"item_code": it.item_code,
				"item_name": it.item_name,
				"description": _line_description(it),
				"qty": qty,
				"uom": it.uom or "",
				"cells": cells,
				"low": low,
				"high": max(rates) if rates else None,
				"low_amount": flt(low * qty, 2) if low is not None else 0,
			}
		)

	totals = []
	for i, q in enumerate(quotes):
		quoted = [r for r in rows if r["cells"][i]]
		value = flt(sum(r["cells"][i]["amount"] for r in quoted), 2)
		# Tax on what was compared: the quotation's own tax, scaled if its net differs (a
		# quantity changed on the quotation), so net + tax stays a like-for-like grand total.
		tax = flt(q.total_taxes_and_charges)
		if flt(q.total) and abs(flt(q.total) - value) > 0.005:
			tax = flt(tax * value / flt(q.total), 2)
		totals.append(
			{
				"quotation": q.name,
				"supplier": q.supplier,
				"supplier_name": q.supplier_name or _supplier_name(q.supplier),
				"valid_till": str(q.valid_till) if q.valid_till else None,
				"status": _sq_status(q),
				"payment_terms": q.payment_terms or "",
				"value": value,
				"tax": tax,
				"grand_total": flt(value + tax, 2),
				"complete": len(quoted) == len(rows),
				"lowest_on": len([r for r in quoted if r["cells"][i]["rate"] == r["low"]]),
			}
		)

	complete = [t for t in totals if t["complete"]]
	best = min(complete, key=lambda t: t["value"]) if complete else None
	answered = {q.supplier for q in quotes}
	return {
		"rfq": {
			"name": rfq.name,
			"subject": rfq.subject or "",
			"project": rfq.get("project"),
			"project_name": _project_name(rfq.get("project")),
			"transaction_date": str(rfq.transaction_date) if rfq.transaction_date else None,
			"status": _state(rfq),
			"suppliers": len(rfq.suppliers),
		},
		"rows": rows,
		"totals": totals,
		"best_quotation": best["quotation"] if best else None,
		"basket": flt(sum(r["low_amount"] for r in rows), 2),
		"pending": [
			s.supplier_name or _supplier_name(s.supplier) for s in rfq.suppliers if s.supplier not in answered
		],
	}
