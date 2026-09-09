import frappe
from frappe import _


@frappe.whitelist()
def get_warehouse_from_project(project: str):
    if project:
        warehouse = frappe.db.get_value("Warehouse", {"project": project, "is_group": 0})
        return warehouse
    else:
        frappe.throw(_("Warehouse Not Found"))

