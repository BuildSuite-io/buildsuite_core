# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Re-apply the BuildSuite permission matrices so the picker-only masters drop to `select`.

Reference masters that a persona only ever resolves in a LINK-FIELD picker (UOM, the tax-template
masters, Construction Trade, Subcontract Delivery Type) were granted full `read` — which also lets
those personas list / report / export the master. `frappe.get_list` (the picker's endpoint) honours
`select`, so the pickers keep working on `select` alone. The setup maps now grant `select` (not
`read`) for those picker-only roles.

Permission setup is install-only, so this patch re-runs the authoritative setup to converge existing
sites onto the new grants (clearing the stale `read`, setting `select`). setup_record_permissions()
is idempotent, so this is safe to re-run."""

from buildsuite_core.permissions.setup import setup_record_permissions


def execute():
	setup_record_permissions()
