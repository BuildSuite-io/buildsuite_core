from buildsuite_core.utils.payment_terms import clear_unused_timing
from buildsuite_core.utils.project import anchor_company_to_project


def set_company(doc, method=None):
	doc.company = None
	anchor_company_to_project(doc)


def clear_milestone_timing(doc, method=None):
	clear_unused_timing(doc.get("payment_milestones") or [])
