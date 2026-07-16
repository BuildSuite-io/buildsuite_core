# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ScheduleSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		kind: DF.Literal["Undo", "Revision"]
		label: DF.Data | None
		project: DF.Link
		root_task: DF.Link | None
		snapshot_data: DF.LongText | None
		task_count: DF.Int
		trigger: DF.Data | None
	# end: auto-generated types

	pass
