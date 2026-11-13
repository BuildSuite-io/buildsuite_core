# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from buildsuite_core.sdk.customisations import clean_config


class BuildSuiteCustomisation(Document):
	def validate(self):
		# Reject anything outside the kind's schema, and store the cleaned form.
		self.config = frappe.as_json(clean_config(self.kind, self.config))
