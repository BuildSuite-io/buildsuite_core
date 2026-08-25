# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Authoritatively re-apply the BuildSuite permission matrices on existing sites.

The per-persona DocPerm matrices in buildsuite_core.permissions.setup are the single
source of truth, but they are only applied on after_install (and via individual
patches) — never re-applied wholesale on migrate. So sites that installed at an older
matrix drift from the code: the Director/Owner review surfaced this across ~13 doctypes
(Measurement Book / Subcontractor Bill / Machinery showing more than read, Customer /
Supplier / Field Employee showing less, Purchase Invoice missing entirely).

This patch heals that drift in one shot by re-running the authoritative setup, which:
  * applies the corrected Director/Owner matrix (Measurement Book + Subcontractor Bill
    down to read-only; Supplier Bill / Purchase Invoice up to full CRWDSX), and
  * re-converges every other doctype's matrix to the code (fixing the stale grants that
    predate this migrate), then re-mirrors child-table / link-target reads last.

setup_record_permissions() is idempotent, so this is safe to re-run."""

from buildsuite_core.permissions.setup import setup_record_permissions


def execute():
	setup_record_permissions()
