# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buildsuite_core.sdk import SDK_VERSION, get_extension_entries, seed_if_missing


def _hooks(entries):
	return patch(
		"frappe.get_hooks", lambda name, *a, **k: entries if name == "buildsuite_frontend_extensions" else []
	)


class TestExtensionEntries(IntegrationTestCase):
	def test_a_valid_entry_is_returned_with_defaults(self):
		with _hooks([{"name": "acme", "js": "/assets/acme/js/x.js"}]):
			self.assertEqual(
				get_extension_entries(),
				[{"name": "acme", "js": "/assets/acme/js/x.js", "css": None, "min_sdk": None}],
			)

	def test_css_and_min_sdk_are_kept(self):
		entry = {"name": "a", "js": "/assets/a/x.js", "css": "/assets/a/x.css", "min_sdk": 1.0}
		with _hooks([entry]):
			self.assertEqual(get_extension_entries()[0]["css"], "/assets/a/x.css")
			self.assertEqual(get_extension_entries()[0]["min_sdk"], "1.0")

	def test_entries_outside_assets_or_malformed_are_dropped(self):
		bad = [
			{"name": "ext", "js": "https://evil.example/x.js"},
			{"name": "trav", "js": "/assets/a/../../etc/x.js"},
			{"name": "proto", "js": "//evil.example/x.js"},
			{"name": "nojs"},
			{"js": "/assets/a/x.js"},
			"not a dict",
		]
		with _hooks(bad):
			self.assertEqual(get_extension_entries(), [])

	def test_a_css_outside_assets_is_ignored_not_fatal(self):
		with _hooks([{"name": "a", "js": "/assets/a/x.js", "css": "https://evil.example/x.css"}]):
			self.assertIsNone(get_extension_entries()[0]["css"])

	def test_duplicate_names_keep_the_first(self):
		with _hooks([{"name": "a", "js": "/assets/a/1.js"}, {"name": "a", "js": "/assets/a/2.js"}]):
			self.assertEqual([e["js"] for e in get_extension_entries()], ["/assets/a/1.js"])

	def test_the_demo_extension_is_discovered_on_a_site_that_has_it(self):
		if "buildsuite_demo_extension" not in frappe.get_installed_apps():
			self.skipTest("demo extension not installed")
		self.assertIn("buildsuite_demo_extension", [e["name"] for e in get_extension_entries()])

	def test_boot_carries_the_entries_and_the_sdk_version(self):
		from buildsuite_core.www.core import get_boot

		boot = get_boot()
		self.assertEqual(boot["buildsuite_sdk_version"], SDK_VERSION)
		self.assertIsInstance(boot["buildsuite_extensions"], list)


class TestSeedIfMissing(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_creates_once_and_never_overwrites(self):
		first = seed_if_missing("Role", {"role_name": "SDK Seed Probe"}, {"desk_access": 1})
		frappe.db.set_value("Role", first.name, "desk_access", 0)
		again = seed_if_missing("Role", {"role_name": "SDK Seed Probe"}, {"desk_access": 1})
		self.assertEqual(first.name, again.name)
		self.assertEqual(frappe.db.get_value("Role", first.name, "desk_access"), 0)
