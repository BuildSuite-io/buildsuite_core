app_name = "buildsuite_core"
app_title = "Buildsuite Core"
app_publisher = "Infraholic Innovations Pvt. Ltd"
app_description = "A construction operating system built on Frappe"
app_email = "app@buildsuite.io"
app_license = "mit"

# Single source of truth for the frontend website route (the SPA is served at
# /<APP_ROUTE> via the www/<APP_ROUTE>.{py,html} page). The `bench change-app-route`
# command rewrites this token, renames the www page, and updates the frontend
# (frontend/src/utils/appRoute.js) to match. Keep all three in sync.
APP_ROUTE = "core"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "buildsuite_core",
		"logo": "/assets/buildsuite_core/images/bs-icon.svg",
		"title": "Buildsuite Core",
		"route": f"/{APP_ROUTE}",
        "has_permission": "buildsuite_core.api.permission.has_app_permission",
	}
]

website_route_rules = [
    {"from_route": f"/{APP_ROUTE}/<path:app_path>", "to_route": APP_ROUTE},
    {"from_route": f"/{APP_ROUTE}", "to_route": APP_ROUTE},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/buildsuite_core/css/buildsuite_core.css"
# app_include_js = "/assets/buildsuite_core/js/buildsuite_core.js"

# include js, css files in header of web template
# web_include_css = "/assets/buildsuite_core/css/buildsuite_core.css"
# web_include_js = "/assets/buildsuite_core/js/buildsuite_core.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "buildsuite_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "buildsuite_core/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "buildsuite_core.utils.jinja_methods",
# 	"filters": "buildsuite_core.utils.jinja_filters"
# }

# Installation
# ------------

after_migrate = "buildsuite_core.install.after_migrate"
before_migrate = "buildsuite_core.install.before_migrate"
# before_install = "buildsuite_core.install.before_install"
after_install = "buildsuite_core.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "buildsuite_core.uninstall.before_uninstall"
# after_uninstall = "buildsuite_core.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "buildsuite_core.utils.before_app_install"
# after_app_install = "buildsuite_core.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "buildsuite_core.utils.before_app_uninstall"
# after_app_uninstall = "buildsuite_core.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "buildsuite_core.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "buildsuite_core.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Project": "buildsuite_core.permissions.project.get_project_permission_query",
    "Task": "buildsuite_core.permissions.task.get_task_permission_query",
    "Work Package": "buildsuite_core.permissions.work_package.get_work_package_permission_query",
    "Task Progress Entry": "buildsuite_core.permissions.task_progress_entry.get_task_progress_entry_permission_query",
    "Stage Planning": "buildsuite_core.permissions.stage_planning.get_stage_planning_permission_query",
}

has_permission = {
    "Project": "buildsuite_core.permissions.project.has_project_permission",
    "Task": "buildsuite_core.permissions.task.has_task_permission",
    "Work Package": "buildsuite_core.permissions.work_package.has_work_package_permission",
    "Task Progress Entry": "buildsuite_core.permissions.task_progress_entry.has_task_progress_entry_permission",
    "Stage Planning": "buildsuite_core.permissions.stage_planning.has_stage_planning_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	# "Project": {
	# 	"validate": "buildsuite_core.utils.project.create_warehouse_for_project",
	# 	"on_trash": "buildsuite_core.utils.project.delete_warehouse_for_project"
	# },
	"Project": {
		"after_insert": "buildsuite_core.utils.project.seed_from_template_on_insert"
	},
	"Task": {
		"validate": ["buildsuite_core.api.schedule.validate_task_dependencies", "buildsuite_core.api.schedule.normalize_milestone_task"],
		"on_update": ["buildsuite_core.utils.task.update_work_package_progress", "buildsuite_core.utils.task.sync_stage_tasks_on_update"],
		"on_trash": ["buildsuite_core.utils.task.recalculate_work_package_on_task_trash", "buildsuite_core.utils.task.sync_stage_tasks_on_delete"]
	},
	# Keep each user's BuildSuite role aligned with their persona. validate covers
	# both create and edit; delete needs no handler (Has Role rows cascade).
	"User": {
		"validate": "buildsuite_core.utils.user.sync_persona_roles"
	}
}
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "buildsuite_core.utils.task.update_delayed_tasks"
    ]
}

# scheduler_events = {
# 	"all": [
# 		"buildsuite_core.tasks.all"
# 	],
# 	"daily": [
# 		"buildsuite_core.tasks.daily"
# 	],
# 	"hourly": [
# 		"buildsuite_core.tasks.hourly"
# 	],
# 	"weekly": [
# 		"buildsuite_core.tasks.weekly"
# 	],
# 	"monthly": [
# 		"buildsuite_core.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "buildsuite_core.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "buildsuite_core.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "buildsuite_core.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "buildsuite_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["buildsuite_core.utils.before_request"]
# after_request = ["buildsuite_core.utils.after_request"]

# Job Events
# ----------
# before_job = ["buildsuite_core.utils.before_job"]
# after_job = ["buildsuite_core.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"buildsuite_core.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

fixtures = [
    {
        "doctype": "Custom HTML Block",
        "filters": [
            ["name", "in", ["Site Execution Workspace"]]
        ]
    },
    # Custom Field and Property Setter are managed via after_migrate / before_migrate
    # hooks in buildsuite_core.install — not as JSON fixtures.
    {
        "doctype": "Workflow State",
        "filters": [
            ["workflow_state_name", "in", [
                "Draft",
                "Pending Approval",
                "Approved",
                "Rejected",
                "Cancelled"
            ]]
        ]
    },
    {
        "doctype": "Workflow Action Master",
        "filters": [
            ["workflow_action_name", "in", [
                "Submit for Approval",
                "Approve",
                "Reject",
                "Revise",
                "Cancel"
            ]]
        ]
    },
    {
        "doctype": "Workflow",
        "filters": [
            ["workflow_name", "in", ["Stage Planning Approval"]]
        ]
    },
]

# include js in doctype views
doctype_js = {
    "Project": "public/js/project.js",
    "Task": "public/js/task.js"
}

doctype_list_js = {
    "Task": "public/js/task_list.js"
}
