# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ProjectSettings(Document):
	"""Site-wide Project settings (Single). Currently the standard project-page tab template
	(`tab_defaults`); a project overrides any of it via its own `custom_tab_overrides`. Other
	project-scoped settings are expected to migrate here from BuildSuite Core Settings later."""

	def on_update(self):
		# The team-scoped workflow list is cached for the per-save hook; drop it on any change.
		from buildsuite_core.utils.team_workflow_notifications import clear_cache

		clear_cache()
