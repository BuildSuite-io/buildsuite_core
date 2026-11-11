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
