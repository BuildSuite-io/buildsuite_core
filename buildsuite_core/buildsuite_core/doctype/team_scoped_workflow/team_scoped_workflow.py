# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class TeamScopedWorkflow(Document):
	"""One document type whose workflow notifications go to the project team (Project Settings >
	Team-scoped workflow notifications; see utils.team_workflow_notifications)."""

	pass
