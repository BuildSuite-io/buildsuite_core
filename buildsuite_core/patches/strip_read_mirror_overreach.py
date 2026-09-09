"""Downgrade the read-mirror's link-target grants from `read` to `select`.

The read mirror (``setup_child_table_read_access``) used to grant `read` on EVERY link-field target
of every doctype a persona could read. `read` also lets a persona list / report / export / open
that master and surfaces its Desk workspace, so following the link graph out of native ERPNext
transactions (Stock Entry -> Work Order, Sales Invoice -> Territory, …) leaked almost all of ERPNext
into every persona — e.g. Foreman could browse BOM and Work Order.

The mirror now grants the minimal ptype for each reference: `read` on child (Table) doctypes,
`select` on Link targets — all a picker / link-validation needs. This patch converges existing
sites: it re-runs the mirror, then strips the leftover `read` from link targets a persona holds
ONLY via the mirror (bare grant, print=0). Child-table reads and authored matrix/mobile grants
(which carry print / write / report flags) are never touched.
"""

import frappe


def execute():
	from buildsuite_core.permissions.setup import BUILDSUITE_ROLES, setup_child_table_read_access

	# Converge the mirror first (adds select on link targets, read on child tables; idempotent).
	setup_child_table_read_access()

	child_tables = set(frappe.get_all("DocType", filters={"istable": 1}, pluck="name"))

	# Bare read-mirror rows: read=1 with none of the flags an authored grant carries. On a LINK
	# target these are now expressed as select-only, so drop the read.
	rows = frappe.get_all(
		"Custom DocPerm",
		filters={
			"role": ["in", list(BUILDSUITE_ROLES)],
			"permlevel": 0,
			"read": 1,
			"print": 0,
			"write": 0,
			"create": 0,
			"submit": 0,
			"cancel": 0,
			"amend": 0,
			"report": 0,
		},
		fields=["name", "parent"],
	)

	stripped = 0
	for r in rows:
		if r.parent in child_tables:
			continue  # child-table read is correct — leave it
		frappe.db.set_value("Custom DocPerm", r.name, "read", 0, update_modified=False)
		stripped += 1

	frappe.clear_cache()
	print(f"strip_read_mirror_overreach: converted {stripped} mirror-only link reads to select-only")
