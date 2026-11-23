# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Sites created fresh got the bespoke reports' Report anchors with the admin roles only.

seed_report_anchors ran before the BuildSuite roles existed on a new site and gives an anchor only
the roles that exist, so no persona could open a Project Finance, Procurement or Workforce report,
or the supplier quotation comparison. Give such an anchor its matrix roles.

Additive only: an anchor is touched only when it has NO persona role at all (that bug's footprint);
an anchor that has any persona role, shipped or an admin's choice, is left exactly as it is, and
no role is ever removed."""

import frappe

from buildsuite_core.report_access import _ADMIN_ROLES, _matrix_roles


def execute():
	for report_name, roles in _matrix_roles().items():
		if not frappe.db.exists("Report", report_name):
			continue
		persona_roles = [r for r in roles if r not in _ADMIN_ROLES and frappe.db.exists("Role", r)]
		doc = frappe.get_doc("Report", report_name)
		have = {r.role for r in doc.roles}
		if not persona_roles or have & set(persona_roles):
			continue
		for role in persona_roles:
			doc.append("roles", {"role": role})
		doc.flags.ignore_permissions = True
		doc.save()
