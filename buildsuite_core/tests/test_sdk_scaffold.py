# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import ast
import tempfile
from pathlib import Path

import frappe
from frappe.tests import UnitTestCase

from buildsuite_core.sdk.extensions import SDK_VERSION
from buildsuite_core.sdk.scaffold import create_extension_app


class TestScaffold(UnitTestCase):
	def test_generates_a_valid_extension_app(self):
		with tempfile.TemporaryDirectory() as tmp:
			root = create_extension_app("acme_ext", "Acme Extension", tmp)
			hooks = ast.parse((root / "acme_ext" / "hooks.py").read_text())
			assigns = {
				t.id: ast.literal_eval(n.value)
				for n in hooks.body
				if isinstance(n, ast.Assign)
				for t in n.targets
			}
			entry = assigns["buildsuite_frontend_extensions"][0]
			self.assertEqual(entry["js"], "/assets/acme_ext/js/extension.js")
			self.assertEqual(entry["min_sdk"], SDK_VERSION)
			self.assertEqual(assigns["required_apps"], ["buildsuite_core"])
			self.assertTrue((root / "acme_ext" / "public" / "js" / "extension.js").exists())

	def test_rejects_bad_names_and_existing_folders(self):
		with tempfile.TemporaryDirectory() as tmp:
			with self.assertRaises(frappe.ValidationError):
				create_extension_app("Bad Name", None, tmp)
			create_extension_app("acme_ext", None, tmp)
			with self.assertRaises(frappe.ValidationError):
				create_extension_app("acme_ext", None, tmp)
			self.assertTrue(Path(tmp, "acme_ext").is_dir())
