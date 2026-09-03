# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Re-run the company backfill after the org-wide ERPNext masters (Supplier / Customer / Item)
gained a `company` field — the original backfill_company_scope patch ran before they were added,
so those rows are still unstamped on existing sites. The backfill is idempotent (stamps only
where company is unset)."""

from buildsuite_core.patches.backfill_company_scope import execute as _backfill


def execute():
	_backfill()
