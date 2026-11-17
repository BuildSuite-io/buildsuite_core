"""Petty Cash Request.disbursement_date ("Paid On") is new. A request disbursed before it takes
the posting date of the Journal Entry that paid it — the date its ledger entries already carry —
so the record and the books agree. Only empty values are filled; no ledger entry is touched."""

import frappe


def execute():
	if not frappe.db.has_column("Petty Cash Request", "disbursement_date"):
		return
	rows = frappe.get_all(
		"Petty Cash Request",
		filters={
			"status": "Disbursed",
			"journal_entry": ["is", "set"],
			"disbursement_date": ["is", "not set"],
		},
		fields=["name", "journal_entry"],
	)
	for row in rows:
		posted = frappe.db.get_value("Journal Entry", row.journal_entry, "posting_date")
		if posted:
			frappe.db.set_value(
				"Petty Cash Request", row.name, "disbursement_date", posted, update_modified=False
			)
