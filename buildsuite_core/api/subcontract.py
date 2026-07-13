# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted endpoints for the Subcontract module — Subcontractor Work Order
read/save (its SOV child table can't be written reliably via frappe.client), the
approval-workflow actions, and the BOQ cost-code picker used on SOV lines."""

import frappe
from frappe.model.workflow import apply_workflow, get_transitions

WORK_ORDER = "Subcontractor Work Order"

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
	"""De-duplicated workflow actions available to the current user (get_transitions
	returns one row per matching allowed-role)."""
	out = []
	for t in get_transitions(doc):
		if t.action not in out:
			out.append(t.action)
	return out


def _serialize(doc):
	return {
		"name": doc.name,
		"subcontractor": doc.subcontractor,
		"subcontractor_name": doc.subcontractor_name,
		"project": doc.project,
		"date": str(doc.date) if doc.date else None,
		"delivery_type": doc.delivery_type,
		"retention_percent": doc.retention_percent,
		"status": doc.status,
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
def apply_wo_action(work_order: str, action: str):
	"""Apply an approval-workflow transition (Submit for Approval / Approve / …)."""
	doc = frappe.get_doc(WORK_ORDER, work_order)
	doc.check_permission("write")
	apply_workflow(doc, action)
	return {"status": doc.status, "actions": _available_actions(doc)}


@frappe.whitelist()
def get_wo_transitions(name: str):
	"""Workflow actions available to the current user for this Work Order."""
	doc = frappe.get_doc(WORK_ORDER, name)
	doc.check_permission("read")
	return _available_actions(doc)


@frappe.whitelist()
def get_project_cost_codes(project: str):
	"""BOQ groups + items for a project, as pickable cost codes for SOV lines."""
	if not project:
		return []
	boqs = frappe.get_all("BOQ", filters={"project": project}, pluck="name")
	if not boqs:
		return []

	# group name by (boq, code) so items can show their group.
	groups = frappe.get_all(
		"BOQ Group", filters={"boq": ["in", boqs]}, fields=["name", "code", "group_name"]
	)
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
