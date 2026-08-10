# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Property Setters applied on install/migrate.

Scope note: these are **global**, site-wide Property Setters — they change the doctype
for every user and every app on the site, including companies that use BuildSuite only
from the Frappe Desk alongside other apps. So this list is deliberately limited to
**functional** customizations (option values BuildSuite's data/logic depend on, a couple
of business-rule mandatory/optional flags). Pure Desk presentation tweaks (hidden fields,
field reordering, list-view columns, standard filters, conditional sections) are NOT set
here — the Vue app renders its own forms and does not need them, and imposing them on the
native Desk is intrusive for Desk-first / multi-app tenants. (The cosmetic setters this
app used to ship are removed on migrate by
patches/remove_cosmetic_desk_property_setters.py.)
"""


def get_property_setters():
	return [
		# --- Option values BuildSuite's features rely on -------------------------------
		{
			# Add "Petty Cash" as a Journal Entry Entry Type. The petty-cash disbursement JE
			# uses it, and the Petty Cash Request link field shows only for this type.
			"doctype_or_field": "DocField",
			"doctype": "Journal Entry",
			"fieldname": "voucher_type",
			"property": "options",
			"value": (
				"Journal Entry\nInter Company Journal Entry\nBank Entry\nCash Entry\n"
				"Credit Card Entry\nDebit Note\nCredit Note\nContra Entry\nExcise Entry\n"
				"Write Off Entry\nOpening Entry\nDepreciation Entry\nAsset Disposal\n"
				"Periodic Accounting Entry\nExchange Rate Revaluation\nExchange Gain Or Loss\n"
				"Deferred Revenue\nDeferred Expense\nPetty Cash"
			),
			"property_type": "Text",
		},
		{
			# A subcontractor is a Supplier tagged supplier_type="Subcontractor".
			"doctype_or_field": "DocField",
			"doctype": "Supplier",
			"fieldname": "supplier_type",
			"property": "options",
			"value": "Company\nIndividual\nPartnership\nSubcontractor",
			"property_type": "Text",
		},
		{
			# BuildSuite's project lifecycle statuses.
			"name": "Project-status-options",
			"doctype_or_field": "DocField",
			"doctype": "Project",
			"fieldname": "status",
			"property": "options",
			"value": "Open\nWorking\nCompleted\nOn Hold\nCancelled",
			"property_type": "Text",
		},
		# --- Business-rule flags -------------------------------------------------------
		{
			# New Tasks default to Activity (BuildSuite's task model).
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "type",
			"property": "default",
			"value": "Activity",
			"property_type": "Text",
		},
		{
			# Cost must attribute to a project: BuildSuite requires it on stock/buying docs.
			"doctype": "Stock Entry",
			"fieldname": "project",
			"property": "reqd",
			"property_type": "Check",
			"value": "1",
		},
		{
			"doctype": "Purchase Order",
			"fieldname": "project",
			"property": "reqd",
			"property_type": "Check",
			"value": "1",
		},
		{
			"doctype": "Purchase Receipt",
			"fieldname": "project",
			"property": "reqd",
			"property_type": "Check",
			"value": "1",
		},
		{
			# Description is optional on a Material Request line (item code carries it).
			"doctype": "Material Request Item",
			"fieldname": "description",
			"property": "reqd",
			"property_type": "Check",
			"value": 0,
		},
		# The naming series auto-generates the record name, so it need not be a required
		# input on these buying docs. (This also keeps the series non-mandatory so it can
		# never re-enter the hidden+mandatory-without-default state that blocked adding
		# custom fields / workflows.)
		{
			"doctype": "Material Request",
			"fieldname": "naming_series",
			"property": "reqd",
			"property_type": "Check",
			"value": "0",
		},
		{
			"doctype": "Purchase Order",
			"fieldname": "naming_series",
			"property": "reqd",
			"property_type": "Check",
			"value": "0",
		},
		{
			"doctype": "Purchase Invoice",
			"fieldname": "naming_series",
			"property": "reqd",
			"property_type": "Check",
			"value": "0",
		},
		{
			"doctype": "Purchase Receipt",
			"fieldname": "naming_series",
			"property": "reqd",
			"property_type": "Check",
			"value": "0",
		},
	]
