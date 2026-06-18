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
            "fieldname": "project_status",
            "fieldtype": "Select",
            "label": "Project Status",
            "insert_after": "status",
            "default": "New",
            "in_list_view": 1,
            "in_standard_filter": 1,
            "options": "New\nOngoing\nDelayed\nCompleted",
            "module": "BuildSuite Core"
        },
        {
            # The assigned Project Manager (a real User). Distinct from `owner`,
            # which Frappe forces to the creating user on insert — so PM
            # assignment must live on its own field. Drives the PM section in the
            # Vue project views.
            "fieldname": "project_manager",
            "fieldtype": "Link",
            "label": "Project Manager",
            "options": "User",
            "insert_after": "project_status",
            "in_standard_filter": 1,
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
            "depends_on": "eval:doc.parent_project",
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
        {
            "fieldname": "task_type",
            "fieldtype": "Select",
            "insert_after": "type",
            "label": "Task Type",
            "in_list_view": 0,
            "in_standard_filter": 1,
            "default": "Activity",
            "options": "Activity\nMilestone\nInspection",
        },
    ],
    "Task Depends On": [
        {
            "fieldname": "dependency_type",
            "fieldtype": "Select",
            "insert_after": "task",
            "label": "Dependency Type",
            "options": "FS\nSS\nFF",
            "default": "FS",
            "in_list_view": 1,
            "description": "FS = Finish-to-Start, SS = Start-to-Start, FF = Finish-to-Finish",
        },
        {
            "fieldname": "lag_days",
            "fieldtype": "Int",
            "insert_after": "dependency_type",
            "label": "Lag (days)",
            "default": "0",
            "in_list_view": 1,
            "description": "Days after the predecessor's constraint date. Negative = lead (allowed overlap).",
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
            "options": "Director / Owner\nProject Manager\nEstimator\nQuantity Surveyor\nSite Engineer\nForeman / Supervisor\nProcurement Officer\nStore Keeper\nAccountant\nHR Manager\nSystem Manager (Admin)\nBuildSuite Administrator",
            "insert_after": "username",
            "module": "BuildSuite Core"
        },
        {
            # The user's company is the source of truth for project company
            # inference (new projects inherit the creator's company). Made
            # mandatory in utils.user when a persona is assigned (server-side only;
            # the Vue user form never shows it — the API stamps the creator's company).
            "fieldname": "company",
            "fieldtype": "Link",
            "label": "Company",
            "options": "Company",
            "insert_after": "persona",
            "module": "BuildSuite Core"
        }
    ]
}
