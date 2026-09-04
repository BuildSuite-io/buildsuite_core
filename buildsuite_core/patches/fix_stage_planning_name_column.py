"""Convert tabStage Planning.name from an integer column to varchar.

Stage Planning names records with the `STG-.YYYY.-.###` series (a string). On sites first created
when the doctype used an Autoincrement name, the `name` column is still an INTEGER column — so
inserting a string name fails with:

    MySQLdb.OperationalError: (1366, "Incorrect integer value: 'STG-2026-001' for column ... name")

Frappe does not auto-convert the `name` column when a doctype's naming changes, so migrate left the
old integer column in place. Convert it to varchar(140) to match the naming. No-op on sites where
the column is already varchar (freshly created ones).
"""

import frappe

DOCTYPE = "Stage Planning"
TABLE = f"tab{DOCTYPE}"
_INT_TYPES = {"bigint", "int", "integer", "mediumint", "smallint", "tinyint"}


def execute():
	if not frappe.db.table_exists(DOCTYPE):
		return

	rows = frappe.db.sql(
		"""
		select lower(data_type)
		from information_schema.columns
		where table_schema = %s and table_name = %s and column_name = 'name'
		""",
		(frappe.conf.db_name, TABLE),
	)
	if not rows or rows[0][0] not in _INT_TYPES:
		return  # already varchar — nothing to do

	# MODIFY to varchar drops any AUTO_INCREMENT attribute the old naming left behind.
	frappe.db.sql_ddl(f"ALTER TABLE `{TABLE}` MODIFY `name` VARCHAR(140)")
	frappe.db.commit()
	print(f"fix_stage_planning_name_column: converted {TABLE}.name to varchar(140)")
