# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WorkspaceSetting(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buildsuite_core.buildsuite_core.doctype.workspace_report.workspace_report import (
			WorkspaceReport,
		)

		reports: DF.Table[WorkspaceReport]
	# end: auto-generated types

	pass
