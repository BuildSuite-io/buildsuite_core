# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Whitelisted save for a Crew. Child tables can't go through frappe.client.

`daily_rate` is not accepted — the child doctype fetches it from the worker.
"""

import frappe
from frappe import _

from buildsuite_core.utils.project import default_company

CREW = "Crew"


def _parse_rows(payload) -> list:
	"""A JSON object parses to a truthy _dict and would iterate its keys."""
	rows = frappe.parse_json(payload) or []
	if not isinstance(rows, list):
		frappe.throw(_("Expected a list of rows."))
	return rows


def _apply_members(doc, rows: list) -> None:
	doc.set("members", [])
	for row in rows:
		row = row or {}
		doc.append(
			"members",
			{
				"field_employee": row.get("field_employee"),
				"role_in_crew": row.get("role_in_crew"),
			},
		)


@frappe.whitelist(methods=["POST"])
def save_crew(
	name: str | None = None,
	crew_name: str | None = None,
	crew_leader: str | None = None,
	trade: str | None = None,
	company: str | None = None,
	members: str | None = None,
) -> dict:
	"""Create or update a crew (gang details + member rows)."""
	rows = _parse_rows(members)

	crew_name = (crew_name or "").strip()
	if not crew_name:
		frappe.throw(_("Crew name is required."))

	if name:
		if not frappe.db.exists(CREW, name):
			frappe.throw(_("Crew {0} no longer exists.").format(name))
		doc = frappe.get_doc(CREW, name)
		doc.check_permission("write")
	else:
		doc = frappe.new_doc(CREW)

	doc.crew_name = crew_name
	doc.crew_leader = crew_leader
	doc.trade = trade
	doc.company = company or default_company()

	_apply_members(doc, rows)

	doc.save()
	return {"name": doc.name}
