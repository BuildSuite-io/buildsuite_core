# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Crew(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.crew_member.crew_member import CrewMember

		company: DF.Link | None
		crew_leader: DF.Link | None
		crew_name: DF.Data
		members: DF.Table[CrewMember]
		members_count: DF.Int
		trade: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_members()
		# Denormalised so the list view can show it — child tables don't come
		# back from frappe.client.get_list.
		self.members_count = len(self.members)

	def validate_members(self):
		"""A worker belongs to a crew once. Enforced here rather than in the save
		API so the Desk grid is covered too."""
		seen = set()
		for row in self.members:
			if not row.field_employee:
				frappe.throw(_("Row {0}: Field Employee is required.").format(row.idx))
			if row.field_employee in seen:
				frappe.throw(
					_("Row {0}: {1} is already a member of this crew.").format(
						row.idx, row.employee_name or row.field_employee
					)
				)
			seen.add(row.field_employee)
