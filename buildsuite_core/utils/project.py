import frappe


@frappe.whitelist()
def create_warehouse_for_project(doc, method=None):
    # Create Projects Group Warehouse
    if not frappe.db.exists(
        "Warehouse",
        {"warehouse_name": "Projects", "company": doc.company}
    ):
        warehouse = frappe.new_doc("Warehouse")
        warehouse.warehouse_name = "Projects"
        warehouse.company = doc.company
        warehouse.is_group = 1
        warehouse.insert(ignore_permissions=True)

    parent_warehouse = frappe.db.get_value(
        "Warehouse",
        {"warehouse_name": "Projects", "company": doc.company},
        "name"
    )

    # Create Project Group Warehouse
    if not frappe.db.exists(
        "Warehouse",
        {"warehouse_name": doc.project_name, "company": doc.company}
    ):
        warehouse = frappe.new_doc("Warehouse")
        warehouse.warehouse_name = doc.project_name
        warehouse.parent_warehouse = parent_warehouse
        warehouse.company = doc.company
        warehouse.is_group = 1
        warehouse.insert(ignore_permissions=True)

    project_parent_warehouse = frappe.db.get_value(
        "Warehouse",
        {"warehouse_name": doc.project_name, "company": doc.company},
        "name"
    )

    # Create Store Warehouse
    project_warehouse = f"{doc.project_name} Store"

    if not frappe.db.exists(
        "Warehouse",
        {"warehouse_name": project_warehouse, "company": doc.company}
    ):
        stock_account = frappe.db.get_value(
            "Account",
            {
                "account_type": "Stock",
                "company": doc.company,
                "is_group": 0
            },
            "name"
        )

        warehouse = frappe.new_doc("Warehouse")
        warehouse.warehouse_name = project_warehouse
        warehouse.project = doc.name
        warehouse.parent_warehouse = project_parent_warehouse
        warehouse.account = stock_account
        warehouse.company = doc.company
        warehouse.insert(ignore_permissions=True)


@frappe.whitelist()
def delete_warehouse_for_project(doc, method=None):
    project_warehouse = f"{doc.project_name} Store"

    warehouse_name = frappe.db.get_value(
        "Warehouse",
        {
            "warehouse_name": project_warehouse,
            "company": doc.company
        },
        "name"
    )

    if warehouse_name:
        frappe.delete_doc(
            "Warehouse",
            warehouse_name,
            ignore_permissions=True
        )
