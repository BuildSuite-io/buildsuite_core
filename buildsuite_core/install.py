import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from buildsuite_core.custom_property_list.custom_field import CUSTOM_FIELD
from buildsuite_core.custom_property_list.property_field import get_property_setters
from buildsuite_core.permissions.setup import setup_child_table_read_access, setup_record_permissions
from buildsuite_core.utils.project import backfill_project_status
from buildsuite_core.utils.task import backfill_native_task_type, backfill_task_status


def after_install():
	print(_("Creating Custom Fields..."))
	create_custom_fields(CUSTOM_FIELD, ignore_validate=True)
	make_property_setters()
	seed_master_data()


def after_migrate():
	print(_("Creating Custom Fields..."))
	create_custom_fields(CUSTOM_FIELD, ignore_validate=True)
	make_property_setters()
	# Backfill task_status + the native `type` on Tasks that predate the fields (idempotent).
	backfill_task_status()
	backfill_native_task_type()
	backfill_project_status()
	# Safety net for the task_type -> native `type` migration: after_migrate runs last,
	# so it reliably removes the retired custom column/record even when the patch's drop
	# (post_model_sync) races with doctype sync on the one-time transition migrate. The
	# native `type` is already populated by backfill_native_task_type() above, so this is
	# safe; it is a no-op on every subsequent migrate.
	drop_legacy_task_type_field()
	backfill_work_order_company()
	backfill_bill_company()
	seed_master_data()
	# Self-heal the reference read-mirror on EVERY migrate. It's purely additive + idempotent
	# (grants only the missing reads, never revokes), so running it LAST — after all patches and
	# fixture syncs this migrate — guarantees the child-table / link-target reads survive any
	# authoritative perm re-apply (e.g. a subcontract patch resetting Supplier's role list) that
	# ran earlier. This removes the "must remember to run the mirror last by hand" footgun.
	setup_child_table_read_access()


def _backfill_project_company(doctype, extra_where=""):
	"""Re-anchor a doctype's `company` to its project's company where they drifted. Idempotent."""
	rows = frappe.db.sql(
		f"""select d.name, p.company as project_company
		from `tab{doctype}` d join `tabProject` p on p.name = d.project
		where d.company != p.company and p.company is not null and p.company != '' {extra_where}""",
		as_dict=True,
	)
	for r in rows:
		frappe.db.set_value(doctype, r.name, "company", r.project_company, update_modified=False)


def backfill_work_order_company():
	"""Re-anchor any Subcontractor Work Order whose company drifted from its project's company
	(historically the WO could inherit the user's default company). The bill's generated PI
	validates the project against this company, so a mismatch would block posting."""
	_backfill_project_company("Subcontractor Work Order")


def backfill_bill_company():
	"""Re-anchor DRAFT Subcontractor Bills whose company drifted from their project's — so the
	Vue tax/account pickers filter to the right company and the PI can post."""
	_backfill_project_company(
		"Subcontractor Bill", extra_where="and d.docstatus = 0 and d.project is not null"
	)


def drop_legacy_task_type_field():
	"""Idempotently remove the retired custom `task_type` Select (column + record).
	Scheduling type now lives on the native `type` Link. No-op once removed."""
	if frappe.db.has_column("Task", "task_type"):
		frappe.db.sql_ddl("alter table `tabTask` drop column `task_type`")
	frappe.db.delete("Custom Field", {"dt": "Task", "fieldname": "task_type"})
	frappe.clear_cache(doctype="Task")


def seed_master_data():
	# Project Categories (our construction categories) — the New Project form and
	# project templates key off these; the native Project Type stays Internal/External.
	from buildsuite_core.buildsuite_core.doctype.project_category.seed_categories import seed_categories

	seed_categories()
	create_item_group()

	# Project Type stays native ERPNext (Internal / External) — construction
	# categories now live in Project Category above. ERPNext ships "External"; we
	# add "Internal". (The legacy category Project Types are pruned by a patch.)
	for pt in ("Internal", "External"):
		if not frappe.db.exists("Project Type", pt):
			frappe.get_doc({"doctype": "Project Type", "project_type": pt}).insert(ignore_permissions=True)

	# Task Type uses Prompt autoname (the type name IS the record name) and has no
	# `task_type` field — set the name directly.
	task_types = ["Activity", "Milestone", "Inspection"]
	for tt in task_types:
		if not frappe.db.exists("Task Type", tt):
			frappe.get_doc({"doctype": "Task Type", "name": tt}).insert(ignore_permissions=True)

	# Project Templates (Commercial / Residential / Infrastructure) — one ERPNext
	# Project Template per Project Category, carrying default work packages, stages
	# and tasks. Idempotent (skips a template that already exists).
	from buildsuite_core.buildsuite_core.doctype.project_category.seed_project_templates import (
		seed_project_templates,
	)

	seed_project_templates()

	# Subcontract module masters — Construction Trades + Work Order Delivery Types.
	from buildsuite_core.buildsuite_core.doctype.subcontractor.seed_subcontract import (
		seed_subcontract_masters,
	)

	seed_subcontract_masters()

	seed_employee_accounting_dimension()
	seed_invoice_terms()
	seed_finance_accounts()


# Sales-invoice Terms & Conditions boilerplate (plain text — kept human-friendly, no HTML).
INVOICE_TERMS = [
	(
		"Standard Sales Invoice",
		"1. Payment: Payment is due by the due date stated on this invoice. Interest may be charged on overdue amounts as per the contract.\n"
		"2. Taxes: Amounts are exclusive of taxes unless stated; GST is charged as itemised on this invoice.\n"
		"3. Disputes: Any discrepancy must be notified in writing within 7 days of receipt of this invoice.\n"
		"4. Remittance: Payment by account-payee instrument or bank transfer to the account communicated separately, quoting this invoice number.",
	),
	(
		"RA / Milestone Billing",
		"1. Basis: This invoice is raised against the certified work-done / milestone stated in the line items, as per the contract billing schedule.\n"
		"2. Certification: Quantities and values are as certified by the client's engineer; recovery of advances and retention (if applicable) is as per contract.\n"
		"3. Payment: Due by the stated due date. Delays beyond the credit period attract interest as per contract.\n"
		"4. Taxes: GST as itemised. TDS, if deducted, must be deposited and certificates furnished within statutory timelines.\n"
		"5. Disputes: Discrepancies must be raised in writing within 7 days; undisputed amounts shall not be withheld.",
	),
	(
		"Advance-adjusted Invoice",
		"1. Adjustment: This invoice is net of advances received and adjusted as itemised/communicated.\n"
		"2. Payment: Balance due by the stated due date to the designated bank account, quoting this invoice number.\n"
		"3. Taxes: GST as itemised on this invoice.\n"
		"4. Disputes: Any discrepancy must be notified in writing within 7 days of receipt.",
	),
]


def seed_invoice_terms():
	"""Seed the standard sales-invoice Terms & Conditions templates (idempotent). Stored as
	plain text so the invoice's terms box shows friendly text, not raw HTML."""
	for title, terms in INVOICE_TERMS:
		if frappe.db.exists("Terms and Conditions", title):
			continue
		frappe.get_doc(
			{"doctype": "Terms and Conditions", "title": title, "selling": 1, "terms": terms}
		).insert(ignore_permissions=True)


# Ledger accounts every BuildSuite finance posting depends on. Users never configure these —
# the generated documents (petty cash, expense reimbursements, subcontractor retention, plant
# recovery) post to/from them. Seeded per company; "Petty Cash" is handled separately because it
# is the imprest float the petty-cash setting points at. (name, root_type, account_type, parent).
# Retention/Reimbursements/Advances carry a BLANK account_type on purpose: the ERPNext "Payable"
# type forces a party subledger on every line, but these are held against the company, not a
# party. Plant Recovery is a contra-expense (credited when internal plant is recovered).
FINANCE_ACCOUNTS = [
	("Petty Cash Advances", "Asset", "", "Current Assets"),
	("Reimbursements Payable", "Liability", "", "Current Liabilities"),
	("Retention Payable", "Liability", "", "Current Liabilities"),
	("Plant Recovery", "Expense", "", "Expenses"),
	("Cash", "Asset", "Cash", "Cash In Hand"),
	("Bank", "Asset", "Bank", "Bank Accounts"),
]


def seed_company_accounts(company):
	"""Create the BuildSuite ledger accounts a finance posting depends on, for ONE company.
	Idempotent — reuses accounts a prior pass (or ERPNext's default CoA) already created."""
	from buildsuite_core.utils.petty_cash import resolve_petty_cash_account
	from buildsuite_core.utils.subcontract_billing import _ensure_account

	resolve_petty_cash_account(company)  # the "Petty Cash" imprest float (Cash In Hand)
	for account_name, root_type, account_type, parent_hint in FINANCE_ACCOUNTS:
		_ensure_account(company, account_name, root_type, account_type, parent_hint)


def seed_finance_accounts():
	"""Seed the finance ledger accounts for EVERY company, then point the petty-cash setting at
	the default company's Petty Cash float. Idempotent; a company that can't be seeded (e.g. a
	part-configured Chart of Accounts) is logged and skipped so it never breaks migrate."""
	for company in frappe.get_all("Company", pluck="name"):
		try:
			seed_company_accounts(company)
		except Exception:
			frappe.log_error(
				title=f"BuildSuite: could not seed finance accounts for {company}"[:140],
				message=frappe.get_traceback(),
			)
	_seed_default_petty_cash_account()


def _seed_default_petty_cash_account():
	"""Default the configurable Petty Cash Account (BuildSuite Core Settings) to the default
	company's seeded 'Petty Cash' ledger — so petty cash and expenses have a float to post
	to/from out of the box. Respects an account an admin has already chosen."""
	from buildsuite_core.utils.petty_cash import resolve_petty_cash_account
	from buildsuite_core.utils.project import default_company

	company = default_company()
	if not company:
		return
	settings = frappe.get_single("BuildSuite Core Settings")
	current = settings.default_petty_cash_account
	if current and frappe.db.exists("Account", current):
		return
	settings.default_petty_cash_account = resolve_petty_cash_account(company)
	settings.flags.ignore_permissions = True
	settings.save()


def seed_employee_accounting_dimension():
	"""Register an 'Employee' Accounting Dimension.

	Lets the petty-cash holder (and any accounting posting) be stamped natively as the
	`employee` dimension on Journal Entry Account / GL Entry — settable on any account
	(Cash/Bank included, where party_type is disallowed) and groupable in the standard
	General Ledger / Financial Statements. ERPNext creates the `employee` Link→Employee
	field on the accounting doctypes on insert; where our (legacy) custom field of the
	same name already exists it is reused, so existing data is preserved. Optional (not
	mandatory) on every voucher.
	"""
	if frappe.db.exists("Accounting Dimension", {"document_type": "Employee"}):
		return
	frappe.get_doc({"doctype": "Accounting Dimension", "document_type": "Employee"}).insert(
		ignore_permissions=True
	)


def create_item_group():
	if frappe.db.get_value("Item Group", "Raw Material"):
		frappe.rename_doc("Item Group", "Raw Material", "Materials", force=1, merge=0)
	if frappe.db.get_value("Item Group", "Asset"):
		frappe.rename_doc("Item Group", "Asset", "Assets", force=1, merge=0)
	frappe.db.commit()


def before_migrate():
	delete_custom_fields(CUSTOM_FIELD)


def delete_custom_fields(custom_fields):
	for doctypes, fields in custom_fields.items():
		if isinstance(fields, dict):
			fields = [fields]

		if isinstance(doctypes, str):
			doctypes = (doctypes,)

		for doctype in doctypes:
			frappe.db.delete(
				"Custom Field",
				{
					"fieldname": ("in", [field["fieldname"] for field in fields]),
					"dt": doctype,
				},
			)

			frappe.clear_cache(doctype=doctype)


def make_property_setters():
	for property_setter in get_property_setters():
		frappe.make_property_setter(property_setter, validate_fields_for_doctype=False)
