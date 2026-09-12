"""The four numbers on the Quotation list cards.

They cover every quotation, not only the rows the user has filtered to, so they
cannot come from the list itself.
"""

import frappe
from frappe.utils import flt, nowdate

# Which ERPNext status means what to an estimator.
# "Replied" is still waiting — a question is not an answer.
# "Partially Ordered" is a win — the customer said yes to part of it.
PIPELINE_STATUSES = ["Open", "Replied"]
WON_STATUSES = ["Ordered", "Partially Ordered"]
LOST_STATUSES = ["Lost"]


@frappe.whitelist()
def get_summary() -> dict:
	"""Pipeline value, won value, win rate and how many have expired."""
	values, counts = _totals_by_status()

	won = _add_up(counts, WON_STATUSES)
	decided = won + _add_up(counts, LOST_STATUSES)

	return {
		"pipeline_value": _add_up(values, PIPELINE_STATUSES),
		"won_value": _add_up(values, WON_STATUSES),
		# None, not 0, when nothing has been decided. 0% would say "you win
		# nothing", which is not the same as "nobody has answered yet".
		"win_rate": round(won / decided * 100) if decided else None,
		"lapsed_count": _lapsed_count(),
	}


def _totals_by_status() -> tuple[dict, dict]:
	"""Rupee total and row count for each status, in one query."""
	rows = frappe.get_list(
		"Quotation",
		filters={"docstatus": ["<", 2]},
		fields=["status", {"COUNT": "name", "as": "count"}, {"SUM": "grand_total", "as": "value"}],
		group_by="status",
	)
	values = {row.status: flt(row.value) for row in rows}
	counts = {row.status: row.count for row in rows}
	return values, counts


def _add_up(totals: dict, statuses: list) -> float:
	"""Total across the given statuses, treating a missing one as zero."""
	return sum(totals.get(status, 0) for status in statuses)


def _lapsed_count() -> int:
	"""Still waiting on the customer, and the validity date has passed."""
	# "is set" matters: Frappe reads an empty date as "", and "" is less than
	# any date. Without it, every quotation with no validity date looks expired.
	return frappe.get_list(
		"Quotation",
		filters=[
			["docstatus", "<", 2],
			["status", "in", PIPELINE_STATUSES],
			["valid_till", "is", "set"],
			["valid_till", "<", nowdate()],
		],
		fields=[{"COUNT": "name", "as": "count"}],
	)[0].count
