import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class ResendEventLog(Document):
	@staticmethod
	def clear_old_logs(days=90):
		"""Called by Log Settings (see default_log_clearing_doctypes in hooks.py)."""
		table = frappe.qb.DocType("Resend Event Log")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))
