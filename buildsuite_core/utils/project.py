import frappe


def seed_from_template_on_insert(doc, method=None):
    if not doc.project_type:
        return
    if not (doc.custom_seed_default_stages or doc.custom_seed_default_tasks):
        return

    template_name = frappe.db.get_value(
        'BuildSuite Project Template',
        {'project_type': doc.project_type},
        'name'
    )
    if not template_name:
        return

    template = frappe.get_doc('BuildSuite Project Template', template_name)

    from buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.buildsuite_project_template import (
        create_stage_plan,
        create_task,
    )

    if doc.custom_seed_default_stages:
        for row in template.stage_plans:
            try:
                stage_plan_doc = frappe.get_doc('Stage Plan Template', row.stage_plan)
                create_stage_plan(doc.name, stage_plan_doc)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f'BuildSuite: seed stage plan "{row.stage_plan}" for project "{doc.name}"'
                )

    if doc.custom_seed_default_tasks:
        for row in template.project_task:
            try:
                create_task(doc.name, row)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f'BuildSuite: seed task "{row.task}" for project "{doc.name}"'
                )


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
