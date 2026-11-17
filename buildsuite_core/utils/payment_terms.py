def clear_unused_timing(rows):
	"""A milestone keeps only the timing its Payable uses: a stage or a day count."""
	for row in rows:
		if row.payable != "Stage completes":
			row.stage = None
		if row.payable != "On a date":
			row.days_after_project_start = None
