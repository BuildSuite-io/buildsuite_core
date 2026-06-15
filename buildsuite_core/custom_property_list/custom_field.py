CUSTOM_FIELD = {
    "Project": [
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
            "fieldname": "custom_team",
            "fieldtype": "Tab Break",
            "label": "Team",
            "insert_after": "custom_stage_planning_html",
            "module": "BuildSuite Core"
        },
        {
            "fieldname": "custom_team_members",
            "fieldtype": "Table",
            "options": "Project Team",
            "label": "Team Members",
            "default": "0",
            "insert_after": "custom_team",
            "module": "BuildSuite Core"
        },
        {
            "fieldname": "custom_scope_changes",
            "fieldtype": "Tab Break",
            "label": "Scope Changes",
            "insert_after": "custom_team_members",
            "module": "BuildSuite Core"
        },
        {
            "fieldname": "custom_seed_default_stages",
            "fieldtype": "Check",
            "label": "Seed Default Stages",
            "default": "0",
            "hidden": 1,
            "insert_after": "project_type",
            "module": "BuildSuite Core"
        },
        {
            "fieldname": "custom_seed_default_tasks",
            "fieldtype": "Check",
            "label": "Seed Default Tasks",
            "default": "0",
            "hidden": 1,
            "insert_after": "custom_seed_default_stages",
            "module": "BuildSuite Core"
        }

    ],
    "Task": [
        {
            # fieldname kept as "work_package" (not "custom_work_package") to match
            # the vue frontend and existing data — frontend calls task.work_package
            "fieldname": "work_package",
            "fieldtype": "Link",
            "label": "Work Package",
            "options": "Work Package",
            "in_list_view": 0,
            "insert_after": "parent_task",
            "module": "BuildSuite Core"
        },
        {
            "fieldname": "custom_task_id",
            "fieldtype": "Data",
            "label": "Task ID",
            "reqd": 0,
            "unique": 0,
            "in_list_view": 1,
            "insert_after": "work_package",
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
        },
        {
            "fieldname": "task_status",
            "fieldtype": "Select",
            "insert_after": "status",
            "label": "Task Status",
            "in_list_view": 0,
            "in_standard_filter": 1,
            "default": "Yet To Start",
            "options": "Yet To Start\nIn Progress\nIn Delay\nCompleted\nBlocked",
        },
    ],
    "Warehouse": [
        {
            "fieldname": "project",
            "fieldtype": "Link",
            "label": "Project",
            "options": "Project",
            "insert_after": "company",
            "module": "BuildSuite Core"
        }
    ],
    "User": [
        {
            "fieldname": "persona",
            "fieldtype": "Select",
            "label": "Persona",
            # Option strings must match the keys in PERSONA_TO_ROLE
            # (buildsuite_core.permissions.setup) and roles.js `name` fields.
            "options": "Director / Owner\nProject Manager\nEstimator\nQuantity Surveyor\nSite Engineer\nForeman / Supervisor\nProcurement Officer\nStore Keeper\nAccountant\nHR Manager\nSystem Manager (Admin)\nBuildSuite Administrator",
            "insert_after": "username",
            "module": "BuildSuite Core"
        }
    ]
}
