import frappe
from frappe.utils import flt, nowdate

QUOTATION = "Quotation"

PIPELINE_STATUSES = ("Open", "Replied")
WON_STATUSES = ("Ordered", "Partially Ordered")
LOST_STATUSES = ("Lost",)
UNDECIDED_STATUSES = ("Open", "Replied", "Expired")


@frappe.whitelist()
def get_summary() -> dict:
	values, counts = _values_and_counts_by_status()
	won = _sum_for(counts, WON_STATUSES)
	decided = won + _sum_for(counts, LOST_STATUSES)

	return {
		"pipeline_value": _sum_for(values, PIPELINE_STATUSES),
		"won_value": _sum_for(values, WON_STATUSES),
		"win_rate": round(won / decided * 100) if decided else None,
		"lapsed_count": _lapsed_count(),
	}


def _values_and_counts_by_status() -> tuple[dict, dict]:
	rows = frappe.get_list(
		QUOTATION,
		fields=["status", {"COUNT": "name", "as": "n"}, {"SUM": "base_grand_total", "as": "value"}],
		group_by="status",
	)
	return (
		{row.status: flt(row.value) for row in rows},
		{row.status: row.n or 0 for row in rows},
	)


def _sum_for(totals: dict, statuses: tuple) -> float:
	return sum(totals.get(status, 0) for status in statuses)


def _lapsed_count() -> int:
	rows = frappe.get_list(
		QUOTATION,
		filters=[
			["status", "in", UNDECIDED_STATUSES],
			["valid_till", "is", "set"],
			["valid_till", "<", nowdate()],
		],
		fields=[{"COUNT": "name", "as": "n"}],
	)
	return rows[0].n if rows else 0
