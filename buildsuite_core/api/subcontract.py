# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Subcontract module — Subcontractor Work Order
read/save (its SOV child table can't be written reliably via frappe.client), the
submittable lifecycle (submit / cancel / amend), and the BOQ cost-code picker used
on SOV lines. The Work Order is natively submittable: state is docstatus, not a
manual status field — Draft (0) → Submitted (1) → Cancelled (2), plus Amend."""

import frappe
from frappe import _

WORK_ORDER = "Subcontractor Work Order"

# docstatus → the label the Vue screens show. There is no "Closed" state anymore.
_WO_STATE = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


def _wo_state(doc):
	return _WO_STATE.get(doc.docstatus, "Draft")


_LINE_FIELDS = (
	"scope",
	"cost_code_type",
	"cost_code_group",
	"cost_code_item",
	"cost_code_label",
	"uom",
	"qty",
	"rate",
)


def _available_actions(doc):
	"""Lifecycle actions for the WO's current docstatus (mirrors the prototype):
	Draft → Edit / Submit / Delete; Submitted → Record measurement / Bill progress /
	Cancel; Cancelled → Amend / Delete."""
	if doc.docstatus == 0:
		return ["edit", "submit", "delete"]
	if doc.docstatus == 1:
		return ["record_measurement", "bill_progress", "cancel"]
	return ["amend", "delete"]


def _serialize(doc):
	return {
		"name": doc.name,
		"subcontractor": doc.subcontractor,
		"subcontractor_name": doc.subcontractor_name,
		"project": doc.project,
		"project_name": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
		"date": str(doc.date) if doc.date else None,
		"delivery_type": doc.delivery_type,
		"retention_percent": doc.retention_percent,
		"docstatus": doc.docstatus,
		"status": _wo_state(doc),
		"amended_from": doc.get("amended_from"),
		"terms_template": doc.terms_template,
		"terms": doc.terms,
		"total_value": doc.total_value,
		"company": doc.company,
		"lines": [
			{
				"name": r.name,
				"scope": r.scope,
				"cost_code_type": r.cost_code_type,
				"cost_code_group": r.cost_code_group,
				"cost_code_item": r.cost_code_item,
				"cost_code_label": r.cost_code_label,
				"uom": r.uom,
				"qty": r.qty,
				"rate": r.rate,
				"amount": r.amount,
			}
			for r in doc.lines
		],
	}


@frappe.whitelist()
def get_work_order(name: str):
	"""A Work Order with its SOV lines and the workflow actions available now."""
	doc = frappe.get_doc(WORK_ORDER, name)
	doc.check_permission("read")
	out = _serialize(doc)
	out["actions"] = _available_actions(doc)
	return out


def _subcontractor_detail(supplier):
	"""Party block for the WO print view. A subcontractor is a Supplier (type=Subcontractor);
	trade + tax id live on the Supplier, contact person/phone/email on its native Contact."""
	if not supplier or not frappe.db.exists("Supplier", supplier):
		return None
	sup = frappe.db.get_value("Supplier", supplier, ["custom_trade", "tax_id"], as_dict=True) or {}
	detail = {"trade": sup.get("custom_trade"), "tax_id": sup.get("tax_id")}
	contact = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Supplier"],
			["Dynamic Link", "link_name", "=", supplier],
		],
		fields=["name", "first_name", "email_id", "mobile_no", "phone"],
		limit=1,
	)
	if contact:
		c = contact[0]
		detail["contact_person"] = c.first_name
		detail["email"] = c.email_id
		detail["phone"] = c.mobile_no or c.phone
	return detail


@frappe.whitelist()
def get_wo_print_data(name: str):
	"""A Work Order enriched with the party/project detail the in-app print view needs
	(subcontractor contact + tax ids, project code/client/location). Single fetch so the
	Vue print page mirrors the seeded Frappe Print Format from one payload."""
	doc = frappe.get_doc(WORK_ORDER, name)
	doc.check_permission("read")
	out = _serialize(doc)
	out["subcontractor_detail"] = _subcontractor_detail(doc.subcontractor)
	out["project_detail"] = (
		frappe.db.get_value(
			"Project",
			doc.project,
			["custom_project_id", "customer", "location"],
			as_dict=True,
		)
		if doc.project
		else None
	)
	return out


@frappe.whitelist()
def save_work_order(
	name=None,
	subcontractor=None,
	project=None,
	date=None,
	delivery_type=None,
	retention_percent=None,
	terms_template=None,
	terms=None,
	lines=None,
):
	"""Create or update a Work Order (header + SOV lines). Line amounts + the total
	are computed by the controller."""
	lines = frappe.parse_json(lines) or []

	if name and frappe.db.exists(WORK_ORDER, name):
		doc = frappe.get_doc(WORK_ORDER, name)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc(WORK_ORDER)

	doc.subcontractor = subcontractor
	doc.project = project
	doc.date = date
	doc.delivery_type = delivery_type
	if retention_percent is not None:
		doc.retention_percent = retention_percent
	doc.terms_template = terms_template
	doc.terms = terms

	doc.set("lines", [])
	for row in lines:
		doc.append("lines", {k: row.get(k) for k in _LINE_FIELDS})

	doc.save()  # create/write permission enforced by Frappe
	return _serialize(doc)


@frappe.whitelist()
def submit_work_order(name: str):
	"""Submit a draft Work Order — it becomes committed cost (docstatus 1)."""
	doc = frappe.get_doc(WORK_ORDER, name)
	doc.check_permission("submit")
	doc.submit()
	return get_work_order(name)


@frappe.whitelist()
def cancel_work_order(name: str):
	"""Cancel a submitted Work Order (blocked by the controller if MBs/Bills reference it)."""
	doc = frappe.get_doc(WORK_ORDER, name)
	doc.check_permission("cancel")
	doc.cancel()
	return get_work_order(name)


@frappe.whitelist()
def amend_work_order(name: str):
	"""Amend a cancelled Work Order — a fresh editable Draft copy linked via amended_from; the
	original stays Cancelled."""
	src = frappe.get_doc(WORK_ORDER, name)
	src.check_permission("amend")
	if src.docstatus != 2:
		frappe.throw(_("Only a cancelled work order can be amended."))
	amended = frappe.copy_doc(src)
	amended.amended_from = name
	amended.docstatus = 0
	amended.flags.ignore_permissions = True
	amended.insert()
	return get_work_order(amended.name)


@frappe.whitelist()
def get_wo_transitions(name: str):
	"""Lifecycle actions available for this Work Order (kept for the Vue action bar)."""
	doc = frappe.get_doc(WORK_ORDER, name)
	doc.check_permission("read")
	return _available_actions(doc)


@frappe.whitelist()
def committed_by_cost_code(project: str):
	"""Sum of SUBMITTED Subcontractor Work Order line amounts for a project, grouped by
	cost-code group. Feeds the BOQ 'Committed' column — how much of each BOQ group's scope is
	already committed to subcontractors. Only submitted (docstatus 1) WOs count as committed;
	drafts and cancelled WOs are excluded."""
	if not project:
		return {}
	wos = frappe.get_all(
		WORK_ORDER,
		filters={"project": project, "docstatus": 1},
		pluck="name",
	)
	if not wos:
		return {}
	rows = frappe.get_all(
		"Subcontractor Work Order Line",
		filters={"parent": ["in", wos]},
		fields=["cost_code_group", "amount"],
	)
	out = {}
	for r in rows:
		code = r.cost_code_group or ""
		if not code:
			continue
		out[code] = out.get(code, 0) + (r.amount or 0)
	return out


@frappe.whitelist()
def subcontract_actual_by_cost_code(project: str):
	"""Sum of SUBMITTED Subcontractor Bill line `this_period_amount` for a project, grouped by
	cost-code group. Feeds the BOQ 'Actual' — the subcontracted spend billed so far. It is ADDED
	to (never replaces) the task-progress actuals. Only submitted (docstatus 1) bills count."""
	if not project:
		return {}
	bills = frappe.get_all(
		"Subcontractor Bill",
		filters={"project": project, "docstatus": 1},
		pluck="name",
	)
	if not bills:
		return {}
	rows = frappe.get_all(
		"Subcontractor Bill Line",
		filters={"parent": ["in", bills]},
		fields=["cost_code_group", "this_period_amount"],
	)
	out = {}
	for r in rows:
		code = r.cost_code_group or ""
		if not code:
			continue
		out[code] = out.get(code, 0) + (r.this_period_amount or 0)
	return out


@frappe.whitelist()
def get_project_cost_codes(project: str):
	"""BOQ groups + items for a project, as pickable cost codes for SOV lines."""
	if not project:
		return []
	boqs = frappe.get_all("BOQ", filters={"project": project}, pluck="name")
	if not boqs:
		return []

	# group name by (boq, code) so items can show their group.
	groups = frappe.get_all("BOQ Group", filters={"boq": ["in", boqs]}, fields=["name", "code", "group_name"])
	group_code_by_name = {g.name: g.code for g in groups}

	out = []
	for g in sorted(groups, key=lambda g: g.code or ""):
		out.append(
			{
				"type": "Group",
				"group_code": g.code,
				"item_code": "",
				"label": f"{g.code} · {g.group_name}",
			}
		)
	items = frappe.get_all(
		"BOQ Item",
		filters={"boq": ["in", boqs]},
		fields=["code", "description", "boq_group"],
		order_by="code asc",
	)
	for it in items:
		desc = (it.description or "")[:50]
		out.append(
			{
				"type": "Item",
				"group_code": group_code_by_name.get(it.boq_group, ""),
				"item_code": it.code,
				"label": f"{it.code} · {desc}",
			}
		)
	return out


# ---------------------------------------------------------------------------
# Measurement Book — site measurements against a Work Order's SOV lines. Each
# entry records Nos x L x B x D -> quantity (or a directly-typed quantity), with
# deduction rows subtracting. Certified books are the source of measured-to-date.
# ---------------------------------------------------------------------------

MEASUREMENT_BOOK = "Measurement Book"

_MB_ENTRY_FIELDS = (
	"description",
	"work_order_line",
	"cost_code_type",
	"cost_code_group",
	"cost_code_item",
	"cost_code_label",
	"uom",
	"nos",
	"length",
	"breadth",
	"depth",
	"quantity",
	"is_deduction",
)


def _serialize_mb(doc):
	return {
		"name": doc.name,
		"work_order": doc.work_order,
		"project": doc.project,
		"date": str(doc.date) if doc.date else None,
		"measured_by": doc.measured_by,
		"certified_by": doc.certified_by,
		"status": doc.status,
		"remarks": doc.remarks,
		"measured_total": doc.measured_total,
		"company": doc.company,
		"entries": [
			{
				"name": r.name,
				"description": r.description,
				"work_order_line": r.work_order_line,
				"cost_code_type": r.cost_code_type,
				"cost_code_group": r.cost_code_group,
				"cost_code_item": r.cost_code_item,
				"cost_code_label": r.cost_code_label,
				"uom": r.uom,
				"nos": r.nos,
				"length": r.length,
				"breadth": r.breadth,
				"depth": r.depth,
				"quantity": r.quantity,
				"is_deduction": r.is_deduction,
			}
			for r in doc.entries
		],
	}


@frappe.whitelist()
def get_work_order_lines(work_order: str):
	"""A Work Order's SOV lines (id + scope + stored cost code + uom) — used to
	pick which line a measurement entry is against, and to default its code/uom."""
	if not work_order:
		return []
	doc = frappe.get_doc(WORK_ORDER, work_order)
	doc.check_permission("read")
	return [
		{
			"name": r.name,
			"scope": r.scope,
			"cost_code_type": r.cost_code_type,
			"cost_code_group": r.cost_code_group,
			"cost_code_item": r.cost_code_item,
			"cost_code_label": r.cost_code_label,
			"uom": r.uom,
		}
		for r in doc.lines
	]


@frappe.whitelist()
def get_measurement_book(name: str):
	"""A Measurement Book with its entries + the parent WO's lines (for labels)."""
	doc = frappe.get_doc(MEASUREMENT_BOOK, name)
	doc.check_permission("read")
	out = _serialize_mb(doc)
	out["wo_lines"] = get_work_order_lines(doc.work_order) if doc.work_order else []
	return out


@frappe.whitelist()
def save_measurement_book(
	name=None,
	work_order=None,
	project=None,
	date=None,
	measured_by=None,
	remarks=None,
	entries=None,
):
	"""Create or update a Measurement Book (header + entries). Only Draft books
	are editable — Certified books feed billed quantity, so editing is blocked."""
	entries = frappe.parse_json(entries) or []

	if name and frappe.db.exists(MEASUREMENT_BOOK, name):
		doc = frappe.get_doc(MEASUREMENT_BOOK, name)
		doc.check_permission("write")
		if doc.status != "Draft":
			frappe.throw("Only Draft measurement books can be edited. Revert to Draft first.")
	else:
		doc = frappe.new_doc(MEASUREMENT_BOOK)

	doc.work_order = work_order
	doc.project = project
	doc.date = date
	doc.measured_by = measured_by
	doc.remarks = remarks

	doc.set("entries", [])
	for row in entries:
		doc.append("entries", {k: row.get(k) for k in _MB_ENTRY_FIELDS})

	doc.save()
	return _serialize_mb(doc)


@frappe.whitelist()
def certify_measurement_book(name: str):
	"""Certify a Draft measurement book — stamps the certifier and locks it."""
	doc = frappe.get_doc(MEASUREMENT_BOOK, name)
	doc.check_permission("write")
	if doc.status == "Certified":
		return _serialize_mb(doc)
	doc.status = "Certified"
	doc.certified_by = frappe.session.user
	doc.save()
	return _serialize_mb(doc)


@frappe.whitelist()
def revert_measurement_book(name: str):
	"""Send a Certified measurement book back to Draft (clears the certifier)."""
	doc = frappe.get_doc(MEASUREMENT_BOOK, name)
	doc.check_permission("write")
	doc.status = "Draft"
	doc.certified_by = None
	doc.save()
	return _serialize_mb(doc)


@frappe.whitelist()
def get_wo_measurements(work_order: str):
	"""Measurement Books against a Work Order + certified measured-to-date per SOV
	line. Powers the WO detail's Measurements tab and its 'measured to date' column."""
	if not work_order:
		return {"books": [], "measured_by_line": {}}

	books = frappe.get_all(
		MEASUREMENT_BOOK,
		filters={"work_order": work_order},
		fields=["name", "date", "status", "measured_total"],
		order_by="date desc",
	)
	entry_counts = {}
	measured_by_line = {}
	for b in books:
		rows = frappe.get_all(
			"Measurement Book Entry",
			filters={"parent": b.name},
			fields=["work_order_line", "quantity", "is_deduction"],
		)
		entry_counts[b.name] = len(rows)
		if b.status != "Certified":
			continue
		for r in rows:
			line = r.work_order_line or ""
			signed = (-1 if r.is_deduction else 1) * (r.quantity or 0)
			measured_by_line[line] = measured_by_line.get(line, 0) + signed

	for b in books:
		b["entries_count"] = entry_counts.get(b.name, 0)

	return {"books": books, "measured_by_line": measured_by_line}
