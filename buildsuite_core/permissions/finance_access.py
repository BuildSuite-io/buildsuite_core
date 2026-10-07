# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Record-level access for Petty Cash Request + Expense Entry.

Visibility rule (confirmed): the finance/admin roles below see EVERY record; every other role
sees only the ones that are THEIRS — either they created it (owner) OR it belongs to them (the
beneficiary: Petty Cash `requested_by`, Expense the holder Employee's linked User). A float an
approver raises FOR someone is therefore visible to that person even though they didn't create it.

Scoping lives here (permission_query_conditions + has_permission), NOT in the `owner` field — so
`owner` stays the real creator and Frappe's if_owner / "Only If Creator" / "Created By" keep
working. Read is owner-or-beneficiary; write/delete/submit/cancel stay with the creator (approvers
reach everything through their see-all roles).
"""

import frappe

# Roles that see every record (not own-scoped), even if they also hold an own-scoped role.
SEE_ALL_ROLES = {
	"System Manager",
	"BuildSuite Administrator",
	"BuildSuite Director",
	"BuildSuite Accountant",
	"BuildSuite PM",
}

# ptypes that only the creator (owner) may perform on an own-scoped user's records; a beneficiary
# who didn't create it may view but not change it.
_OWNER_ONLY_PTYPES = {"write", "delete", "submit", "cancel", "amend"}


def _is_own_scoped(user):
	return not (set(frappe.get_roles(user)) & SEE_ALL_ROLES)


def _employee_subquery(user):
	# Employees whose linked User is `user` — the beneficiary side of an Expense Entry.
	return f"(SELECT `name` FROM `tabEmployee` WHERE `user_id` = {frappe.db.escape(user)})"


# --------------------------------------------------------------------------- #
# Petty Cash Request — beneficiary is `requested_by` (a User)
# --------------------------------------------------------------------------- #
def get_petty_cash_permission_query(user):
	if not user:
		user = frappe.session.user
	if not _is_own_scoped(user):
		return ""
	u = frappe.db.escape(user)
	return f"(`tabPetty Cash Request`.`owner` = {u} OR `tabPetty Cash Request`.`requested_by` = {u})"


def has_petty_cash_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if not _is_own_scoped(user):
		return True
	if ptype == "create" or not getattr(doc, "name", None):
		return True
	if ptype in _OWNER_ONLY_PTYPES:
		return doc.owner == user  # only the creator changes it
	return doc.owner == user or doc.get("requested_by") == user  # read: creator OR beneficiary


# --------------------------------------------------------------------------- #
# Expense Entry — beneficiary is the holder Employee's linked User
# --------------------------------------------------------------------------- #
def get_expense_permission_query(user):
	if not user:
		user = frappe.session.user
	if not _is_own_scoped(user):
		return ""
	u = frappe.db.escape(user)
	return (
		f"(`tabExpense Entry`.`owner` = {u} "
		f"OR `tabExpense Entry`.`employee` IN {_employee_subquery(user)})"
	)


def has_expense_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if not _is_own_scoped(user):
		return True
	if ptype == "create" or not getattr(doc, "name", None):
		return True
	if ptype in _OWNER_ONLY_PTYPES:
		return doc.owner == user
	if doc.owner == user:
		return True
	beneficiary = frappe.db.get_value("Employee", doc.employee, "user_id") if doc.get("employee") else None
	return beneficiary == user
