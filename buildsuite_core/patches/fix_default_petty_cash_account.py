# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The seeded Petty Cash Account could be a group (the UAE/SG/TH charts ship "Petty Cash" as a
group), which Journal Entries reject. Re-run the seeder: it clears an invalid stored account and
fills a valid ledger when there is exactly one candidate, else leaves it for the admin to choose."""

from buildsuite_core.utils.petty_cash import seed_default_petty_cash_account


def execute():
	seed_default_petty_cash_account()
