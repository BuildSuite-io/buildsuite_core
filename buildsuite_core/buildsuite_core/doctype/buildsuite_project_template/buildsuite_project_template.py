# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BuildSuiteProjectTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.project_stage_plan_template.project_stage_plan_template import ProjectStagePlanTemplate
		from erpnext.projects.doctype.project_template_task.project_template_task import ProjectTemplateTask
		from frappe.types import DF

		project_task: DF.Table[ProjectTemplateTask]
		project_type: DF.Link | None
		stage_plans: DF.Table[ProjectStagePlanTemplate]
		template_name: DF.Data | None
	# end: auto-generated types

	pass
