CUSTOM_FIELD = {
   "Project":[
      {
        "fieldname": "custom_project_id",
        "fieldtype": "Data",
        "label": "Project ID",
        "reqd": 1,
        "unique": 1,
        "in_list_view": 1,
        "insert_after": "project_name",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "is_group",
        "fieldtype": "Check",
        "label": "Is Group",
        "default": "0",
        "insert_after": "company",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "parent_project",
        "fieldtype": "Link",
        "label": "Parent Project",
        "options": "Project",
        "depends_on": "eval:doc.is_group==0",
        "insert_after": "is_group",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_subprojects",
        "fieldtype": "Tab Break",
        "label": "Subprojects",
        "insert_after": "actual_end_date",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_subprojects_html",
        "fieldtype": "HTML",
        "label": "Subprojects HTML",
        "insert_after": "custom_subprojects",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_work_packages",
        "fieldtype": "Tab Break",
        "label": "Work Packages",
        "insert_after": "custom_subprojects_html",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_work_packages_html",
        "fieldtype": "HTML",
        "label": "Work Packages HTML",
        "insert_after": "custom_work_packages",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_tasks",
        "fieldtype": "Tab Break",
        "label": "Tasks",
        "insert_after": "custom_work_packages_html",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_tasks_html",
        "fieldtype": "HTML",
        "label": "Tasks HTML",
        "insert_after": "custom_tasks",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_stage_planning",
        "fieldtype": "Tab Break",
        "label": "Stage Planning",
        "insert_after": "custom_tasks_html",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_stage_planning_html",
        "fieldtype": "HTML",
        "label": "Stage Planning HTML",
        "insert_after": "custom_stage_planning",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_scope_changes",
        "fieldtype": "Tab Break",
        "label": "Scope Changes",
        "insert_after": "custom_stage_planning_html",
        "module": "BuildSuite Core"
    }
   ],
   "Task":[
      {
        "fieldname": "custom_work_package",
        "fieldtype": "Link",
        "label": "Work Package",
        "options": "Work Package",
        "reqd": 1,
        "in_list_view": 1,
        "insert_after": "status",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "custom_task_id",
        "fieldtype": "Data",
        "label": "Task ID",
        "reqd": 1,
        "unique": 1,
        "in_list_view": 1,
        "insert_after": "custom_work_package",
        "module": "BuildSuite Core"
    },
    {
        "fieldname": "task_progress_details",
        "fieldtype": "Table",
        "label": "Task Progress Details",
        "options": "Task Progress Details",
        "insert_after": "description",
        "module": "BuildSuite Core",
        "read_only": 1
    }
   ],
   "Warehouse":[
      {
        "fieldname": "project",
        "fieldtype": "Link",
        "label": "Project",
        "options": "Project",
        "insert_after": "company",
        "module": "BuildSuite Core"
    }
   ]
}