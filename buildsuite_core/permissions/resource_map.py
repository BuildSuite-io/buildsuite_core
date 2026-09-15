"""Frontend resource-key → Doctype map — the seam for backend-derived UI gating.

The Vue SPA gates its New / Edit / Delete affordances with camelCase "resource" keys
(e.g. ``canCreate('rateMaster')``). Historically each key carried a hand-maintained
capability matrix in ``frontend/src/data/roles.js`` (``PERSONA_CAPS`` / ``_MODULE_ACCESS``)
that mirrored ``permissions/setup.py`` by hand and drifted from it.

This module is the ONE place that says which Doctype backs each key, so the SPA can
DERIVE its gating from ``frappe.has_permission`` (see ``api.permission.get_resource_permissions``)
instead of duplicating the matrix. Server-side enforcement is unchanged — the derived
payload is a UI convenience only.

Notes on the mapping:
* ``subcontractor`` and ``supplier`` are INTENTIONAL ALIASES — both back onto ``Supplier``
  (a subcontractor is a Supplier of type "Subcontractor"), so they necessarily resolve to
  identical caps. The two keys exist only for call-site readability (the Subcontract screens
  vs the Suppliers panel); they cannot be gated apart, because DocPerms are doctype-level, not
  per-type. (The retired client matrix gave them *different* read sets — an impossible
  distinction the backend correctly collapses. Screen-level visibility that used to lean on
  that split is handled by the workspace registry instead.) The alias is enforced by
  test_permission_matrix.TestResourcePermissionDerivation.
* ``materialConsumption`` is a ``Stock Entry`` of type "Material Issue", ``supplierBill``
  a ``Purchase Invoice``, ``advance`` a ``Payment Entry`` — the DocPerm is at the Doctype
  level, which is exactly what the corresponding ``*_ROLE_PERMS`` matrix governs.
* Several targets are native ERPNext/Frappe Doctypes, not BuildSuite custom ones — the
  map spans the union, matching the permission matrices in ``permissions/setup.py``.
"""

# camelCase resource key (as used by usePermissions / roles.js) → backing Doctype.
RESOURCE_DOCTYPES = {
	# Site execution (the former PERSONA_CAPS core resources)
	"project": "Project",
	"workPackage": "Work Package",
	"task": "Task",
	"taskProgressEntry": "Task Progress Entry",
	"stagePlanning": "Stage Planning",
	"sco": "Scope Change Order",
	# Procurement
	"materialRequest": "Material Request",
	"purchaseOrder": "Purchase Order",
	"purchaseReceipt": "Purchase Receipt",
	"materialConsumption": "Stock Entry",  # type "Material Issue"
	"item": "Item",
	# Estimation
	"boq": "BOQ",
	"assembly": "Assembly",
	"estimateTemplate": "Estimate Template",
	"rateMaster": "Construction Rate Master",
	# Subcontract
	"subcontractor": "Supplier",  # Supplier of type "Subcontractor"
	"subcontractorWorkOrder": "Subcontractor Work Order",
	"measurementBook": "Measurement Book",
	"subcontractorBill": "Subcontractor Bill",
	# Workforce
	"fieldEmployee": "Employee",
	"crew": "Crew",
	"fieldAttendance": "Field Attendance",
	# Equipment
	"machinery": "Machinery",
	"machineryUsage": "Machinery Usage",
	# Project Finance
	"supplier": "Supplier",
	"customer": "Customer",
	"supplierBill": "Purchase Invoice",
	"salesInvoice": "Sales Invoice",
	"advance": "Payment Entry",
	"pettyCash": "Petty Cash Request",
	"expense": "Expense Entry",
}
