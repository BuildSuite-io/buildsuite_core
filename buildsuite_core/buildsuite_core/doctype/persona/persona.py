# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Persona(Document):
	def validate(self):
		# Default the slug from the name so the frontend always has a stable id.
		if not (self.slug or "").strip():
			self.slug = frappe.scrub(self.persona_name or "").replace("_", "-")
