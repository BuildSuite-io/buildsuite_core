# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ProjectTabVisibility(Document):
	"""One project-detail tab's visibility (tab id + shown). Reused as a child row on both the
	Project Settings Single (the site-wide template) and Project (`custom_tab_overrides`, a sparse
	per-project override). The tab catalogue itself lives in the SPA (frontend/src/data/projectTabs.js);
	this only stores the boolean keyed by tab id."""

	pass
