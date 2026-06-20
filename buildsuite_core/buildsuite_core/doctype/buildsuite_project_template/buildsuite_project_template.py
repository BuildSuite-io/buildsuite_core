# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.exceptions import ValidationError
from frappe.model.document import Document


class BuildSuiteProjectTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.projects.doctype.project_template_task.project_template_task import ProjectTemplateTask
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.project_stage_plan_template.project_stage_plan_template import (
			ProjectStagePlanTemplate,
		)

		project_task: DF.Table[ProjectTemplateTask]
		project_type: DF.Link
		stage_plans: DF.Table[ProjectStagePlanTemplate]
		template_name: DF.Data | None
	# end: auto-generated types

	pass


def create_erpnext_project_from_template(template):
	if not isinstance(template, dict) or "template_name" not in template:
		raise ValueError("Invalid template format")

	project = frappe.new_doc("Project")
	project.project_name = template.get("template_name", "")
	project.custom_project_id = frappe.generate_hash(length=10)
	project.insert(ignore_permissions=True)

	for project_task_row in template.get("project_task", []):
		create_task(project.name, project_task_row)

	for stage_plan_row in template.get("stage_plans", []):
		# Each row only has a 'stage_plan' link — fetch the actual Stage Plan Template doc
		stage_plan_doc = frappe.get_doc("Stage Plan Template", stage_plan_row.get("stage_plan"))
		create_stage_plan(project.name, stage_plan_doc)

	return project.name


def create_stage_plan(project_name, stage_plan_doc, with_tasks=True):
	stage_plan = frappe.new_doc("Stage Planning")
	stage_plan.project = project_name
	stage_plan.stage_name = stage_plan_doc.stage_name
	stage_plan.insert(ignore_permissions=True)

	# with_tasks=False creates an empty stage (the "Stage Planning only" seed
	# mode). When True, each template task becomes a live Task linked into the
	# stage's child table with a default planned qty of 100% — matching what the
	# frontend stage-create form sets (StageTaskPicker defaults plannedQty: 100).
	if with_tasks:
		for task_row in stage_plan_doc.tasks:
			task_name = create_task(project_name, task_row)
			stage_plan.append(
				"stage_planning_tasks",
				{
					"task": task_name,
					"planned_qty": 100,
					"qty_unit": "%",
				},
			)
		stage_plan.save(ignore_permissions=True)


def create_task(project_name, task_row):
	# task_row.task links to a template Task — copy its properties into a new live Task
	template_task = frappe.get_doc("Task", task_row.task)
	task = frappe.new_doc("Task")
	task.project = project_name
	task.subject = template_task.subject
	task.exp_start_date = template_task.exp_start_date
	task.exp_end_date = template_task.exp_end_date
	task.expected_time = template_task.expected_time
	task.is_template = 0
	task.insert(ignore_permissions=True)
	return task.name


def dummy_project_from_template():
	# This function is a placeholder to demonstrate how to use the create_erpnext_project_from_template function.
	# In a real implementation, you would replace the template data with actual data from your application.
	# bench execute buildsuite_core.buildsuite_core.doctype.buildsuite_project_template.buildsuite_project_template.dummy_project_from_template

	template = frappe.get_doc("BuildSuite Project Template", "Demo")

	project_name = create_erpnext_project_from_template(template.as_dict())
	frappe.logger().info(f"Project created: {project_name}")
