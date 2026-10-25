# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Owner-managed payment schedule templates for Sales offers."""

import math

import frappe
from frappe import _
from frappe.utils import cint

DOCTYPE = "BuildSuite Payment Terms Template"
TRIGGERS = {"signing", "stage", "date", "running"}


def _rows(value):
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if value is None:
		return []
	if not isinstance(value, list):
		frappe.throw(_("Milestones must be a list."))

	rows = []
	for row in value:
		if not isinstance(row, dict):
			frappe.throw(_("Each milestone must be an object."))
		trigger = (row.get("trigger") or "stage").strip()
		if trigger not in TRIGGERS:
			frappe.throw(_("Invalid payment trigger: {0}").format(trigger))
		try:
			percent = float(row.get("percent") or 0)
		except (TypeError, ValueError):
			frappe.throw(_("Milestone percentages must be numbers."))
		if not math.isfinite(percent) or percent < 0 or percent > 100:
			frappe.throw(_("Milestone percentages must be between 0 and 100."))

		days_after = row.get("days_after")
		if days_after in ("", None):
			days_after = None
		elif trigger == "date":
			try:
				days_after = int(days_after)
			except (TypeError, ValueError):
				frappe.throw(_("Date triggers need a whole number of days."))
			if days_after < 0:
				frappe.throw(_("Days after project start cannot be negative."))
		else:
			days_after = None

		rows.append(
			{
				"milestone": (row.get("milestone") or "").strip(),
				"trigger": trigger,
				"stage_key": (row.get("stage_key") or "").strip() or None,
				"days_after": days_after,
				"percent": percent,
				"certify": cint(row.get("certify")),
			}
		)
	return rows


def _as_dict(doc):
	return {
		"id": doc.name,
		"name": doc.title,
		"project_type": doc.project_category or "",
		"description": doc.description or "",
		"enabled": bool(doc.enabled),
		"rows": [
			{
				"id": row.name,
				"milestone": row.milestone or "",
				"trigger": row.trigger,
				"stage_key": row.stage_key or None,
				"days_after": row.days_after,
				"percent": row.percent or 0,
				"certify": bool(row.certify),
			}
			for row in doc.milestones
		],
	}


@frappe.whitelist()
def payment_terms_access():
	"""Permission flags for the Sales payment schedule template library."""
	return {
		"can_read": bool(frappe.has_permission(DOCTYPE, "read")),
		"can_create": bool(frappe.has_permission(DOCTYPE, "create")),
		"can_write": bool(frappe.has_permission(DOCTYPE, "write")),
		"can_delete": bool(frappe.has_permission(DOCTYPE, "delete")),
	}


@frappe.whitelist()
def list_payment_terms_templates():
	"""Return templates the current user may read, including their milestone rows."""
	if not frappe.has_permission(DOCTYPE, "read"):
		frappe.throw(_("You do not have permission to read payment terms templates."), frappe.PermissionError)
	return [
		_as_dict(frappe.get_doc(DOCTYPE, row.name))
		for row in frappe.get_list(
			DOCTYPE,
			fields=["name"],
			order_by="title asc",
			limit_page_length=0,
		)
	]


@frappe.whitelist()
def save_payment_terms_template(
	name=None,
	title=None,
	project_category=None,
	description=None,
	enabled=1,
	milestones=None,
):
	"""Create or update a payment schedule template; DocPerms enforce owner-only changes."""
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the template a name."))
	rows = _rows(milestones)

	if name:
		doc = frappe.get_doc(DOCTYPE, name)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc(DOCTYPE)
		doc.check_permission("create")

	doc.title = title
	doc.project_category = (project_category or "").strip() or None
	doc.description = (description or "").strip()
	doc.enabled = cint(enabled)
	doc.set("milestones", [])
	for row in rows:
		doc.append("milestones", row)

	if name:
		doc.save()
	else:
		doc.insert()
	return _as_dict(doc)


@frappe.whitelist()
def delete_payment_terms_template(name):
	"""Delete a template after checking the caller's DocPerms."""
	doc = frappe.get_doc(DOCTYPE, name)
	doc.check_permission("delete")
	frappe.delete_doc(DOCTYPE, name)
	return {"ok": True}
