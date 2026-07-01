import frappe


@frappe.whitelist()
def get_warehouse_from_project(project):
    if project:
        warehouse = frappe.db.get_value("Warehouse",{'project':project,'is_group':0})
        return warehouse
    else:
        frappe.throw("Warehouse Not Found")

