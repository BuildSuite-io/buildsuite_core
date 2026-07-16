import frappe

def execute():
	frappe.db.set_single_value('BuildSuite Core Settings', 'rate_master_update_threshold', 5)
