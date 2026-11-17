# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Persona(Document):
	def validate(self):
		# Default the slug from the name so the frontend always has a stable id.
		if not (self.slug or "").strip():
			self.slug = frappe.scrub(self.persona_name or "").replace("_", "-")

	def on_update(self):
		self.sync_users_roles()

	def sync_users_roles(self):
		"""Give the users who hold this persona its new role set.

		A user's roles are copied from their persona only when the user is saved
		(utils.user.sync_persona_roles), so without this an admin who edits a persona's
		roles would leave its existing users on the old set. The roles the persona no
		longer grants are taken off them — never a protected role, never one added to the
		user by hand — and saving the user grants the ones it now adds."""
		from buildsuite_core.utils.user import PROTECTED_ROLES, persona_roles

		before = self.get_doc_before_save()
		if not before:
			return
		old = {r.role for r in before.roles}
		new = {r.role for r in self.roles}
		if old == new:
			return

		strip = (persona_roles(before) - persona_roles(self)) - PROTECTED_ROLES
		for name in frappe.get_all("User", filters={"persona": self.name}, pluck="name"):
			user = frappe.get_doc("User", name)
			user.roles = [row for row in user.roles if row.role not in strip]
			# The persona's editor may change it, so its users follow — whether or not that
			# editor may edit those User records directly.
			user.flags.ignore_permissions = True
			user.save()
