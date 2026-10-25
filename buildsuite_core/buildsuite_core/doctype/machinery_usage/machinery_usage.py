# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buildsuite_core.utils.project import anchor_company_to_project, assert_same_company


class MachineryUsage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cost_code_group: DF.Data | None
		cost_code_item: DF.Data | None
		cost_code_label: DF.Data | None
		cost_code_type: DF.Literal["", "Group", "Item"]
		date: DF.Date | None
		fuel_cost: DF.Currency
		machine: DF.Link
		project: DF.Link | None
		quantity: DF.Float
		rate: DF.Currency
		task: DF.Link | None
		unit: DF.Literal["Days", "Hours"]
	# end: auto-generated types

	def validate(self):
		anchor_company_to_project(self)
		self.validate_machine_active()
		# The machine is company-scoped — it must belong to this usage's (project's) company.
		assert_same_company(self, "machine", "Machinery", _("Machine"))

		self.clear_cost_code_on_project_change()
		self.validate_cost_code()

		# The task is optional, but if set it must belong to the selected project —
		# a usage log must never be booked against a task from another project.
		if self.task and self.project:
			task_project = frappe.db.get_value("Task", self.task, "project")
			if task_project != self.project:
				frappe.throw(_("Task {0} does not belong to project {1}.").format(self.task, self.project))

	def clear_cost_code_on_project_change(self):
		before = self.get_doc_before_save()
		if before and before.project != self.project and self.has_value_changed("project"):
			if not self.has_value_changed("cost_code_group") and not self.has_value_changed("cost_code_item"):
				self.cost_code_type = self.cost_code_group = self.cost_code_item = self.cost_code_label = ""

	def validate_cost_code(self):
		"""The cost code is a BOQ group or line from the project's approved estimate. A coded
		log posts quantity x rate + fuel to the BOQ Actual (see api.boq_actuals); an uncoded
		one does not, and says so."""
		from buildsuite_core.api.subcontract import get_project_cost_codes

		if not (self.cost_code_group or self.cost_code_item):
			self.cost_code_type = self.cost_code_group = self.cost_code_item = self.cost_code_label = ""
			if self.project:
				frappe.msgprint(
					_("This log has no cost code, so its cost is not posted to the BOQ Actual."),
					indicator="orange",
					alert=True,
				)
			return

		if not self.project:
			frappe.throw(_("Select a project before choosing a cost code."))

		is_item = bool(self.cost_code_item)
		for c in get_project_cost_codes(self.project):
			if is_item and c["type"] == "Item" and c["item_code"] == self.cost_code_item:
				break
			if not is_item and c["type"] == "Group" and c["group_code"] == self.cost_code_group:
				break
		else:
			frappe.throw(
				_("Cost code {0} is not in the approved estimate of project {1}.").format(
					self.cost_code_item or self.cost_code_group, self.project
				)
			)
		self.cost_code_type = "Item" if is_item else "Group"
		self.cost_code_group = c["group_code"]
		self.cost_code_item = c["item_code"] if is_item else ""
		self.cost_code_label = c["label"]

	def validate_machine_active(self):
		machine = frappe.db.get_value("Machinery", self.machine, ["status", "machinery_name"], as_dict=True)

		if machine and machine.status == "Inactive":
			frappe.throw(
				_("Machinery {0} is Inactive. Usage cannot be logged against it.").format(
					machine.machinery_name or self.machine
				)
			)
