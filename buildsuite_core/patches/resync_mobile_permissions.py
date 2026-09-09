# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Apply the companion mobile app's extra DocPerms to existing sites.

Record permissions are seeded on install only, so a new perm set (here setup_mobile_permissions)
doesn't reach existing sites without a patch. setup_record_permissions() is idempotent, so this
re-runs the whole authoritative seed safely."""

from buildsuite_core.permissions.setup import setup_record_permissions


def execute():
	setup_record_permissions()
