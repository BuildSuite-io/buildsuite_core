app_name = "buildsuite_demo_extension"
app_title = "BuildSuite Demo Extension"
app_publisher = "BuildSuite"
app_description = "Demo extension for BuildSuite Core"
app_email = "dev-admin@buildsuite.io"
app_license = "mit"

required_apps = ["buildsuite_core"]

# The one BuildSuite-specific line: the SPA loads this module at runtime, on sites where this app
# is installed (see buildsuite_core.sdk).
buildsuite_frontend_extensions = [
	{
		"name": "buildsuite_demo_extension",
		"js": "/assets/buildsuite_demo_extension/js/extension.js",
		"min_sdk": "1.0",
	},
]

# A settings page with no JavaScript: a Single DocType. Core lists it on the Settings page and
# renders it with the generic form (see buildsuite_core.sdk.settings_pages).
buildsuite_settings_pages = [
	{
		"doctype": "Demo Extension Settings",
		"group": "Demo extension",
		"label": "Demo extension settings",
		"description": "A settings page added by an installed app, as a Single DocType",
	},
]

# The Custom Field the demo adds to Quotation, Project and Task (the control for it is in public/js/extension.js).
fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Quotation-demo_region",
					"Project-demo_region",
					"Task-demo_region",
					"Work Package-demo_region",
				],
			]
		],
	}
]
