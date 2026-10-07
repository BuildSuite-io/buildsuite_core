from buildsuite_core.utils.project import anchor_company_to_project


def set_company(doc, method=None):
	doc.company = None
	anchor_company_to_project(doc)
