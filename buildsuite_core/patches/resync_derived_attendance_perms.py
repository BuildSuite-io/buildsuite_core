"""Reset the derived attendance registers to read-only for the mobile field-attendance roles.

The mobile-permissions sheet (resync_mobile_permissions) granted the full lifecycle
(write / create / submit / cancel) on the Labour and Overtime Attendance Registers. Those
registers are DERIVED — generated when a Field Attendance muster is submitted — so "no role edits
directly" (DERIVED_ATTENDANCE_ROLE_PERMS). setup.py no longer grants mobile full on them; this
converges existing sites by re-applying the workforce matrix (which resets the registers to
read-only) and the corrected mobile grants (which no longer touch the registers).
"""

import frappe


def execute():
	from buildsuite_core.permissions.setup import (
		setup_mobile_permissions,
		setup_workforce_permissions,
	)

	setup_workforce_permissions()  # re-applies DERIVED_ATTENDANCE_ROLE_PERMS -> registers read-only
	setup_mobile_permissions()  # corrected: no longer grants full on the derived registers
	frappe.clear_cache()
	print("resync_derived_attendance_perms: attendance registers reset to read-only")
