# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StagePlanTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from buildsuite_core.buildsuite_core.doctype.stage_plan_task_template.stage_plan_task_template import StagePlanTaskTemplate
		from frappe.types import DF

		stage_name: DF.Data
		tasks: DF.Table[StagePlanTaskTemplate]
	# end: auto-generated types

	pass
