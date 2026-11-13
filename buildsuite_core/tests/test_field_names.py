"""A DeskField `name` is how an installed app addresses a Core field (fieldRules, the field anchors),
so the names are public: stable, snake_case, unique on a screen, present on every field of the forms
that adopted useExtensionFields, and listed in docs/extension-sdk-form-fields.md."""

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"
spec = importlib.util.spec_from_file_location("form_fields", ROOT / "frontend" / "sdk-kit" / "form_fields.py")
form_fields = importlib.util.module_from_spec(spec)
spec.loader.exec_module(form_fields)

# Fields that stay unnamed on purpose, per file: other forms inside the same screen (Task detail's
# progress entry and dependency forms are other DocTypes), file uploads and read-only displays. A new
# field in any other file must be named; lower these numbers when one is named.
UNNAMED = {
	"views/NewMachineryUsageView.vue": 1,
	"views/NewMeasurementBookView.vue": 2,
	"views/NewTaskProgressEntryView.vue": 1,
	"views/TaskDetailView.vue": 18,
}
# The same field on both sides of a v-if / v-else (the direct-bill and measured-bill layouts)
REPEATED_ALLOWED = {"views/NewSubcontractorBillView.vue"}


class TestFieldNames(unittest.TestCase):
	def test_names_are_snake_case_and_unique_per_screen(self):
		seen = 0
		for path in SRC.rglob("*.vue"):
			rel = path.relative_to(SRC).as_posix()
			names = [
				m.group(1)
				for a, _ in form_fields.FIELD.findall(path.read_text())
				if (m := form_fields.NAMED.search(a))
			]
			seen += len(names)
			for n in names:
				self.assertRegex(n, r"^[a-z][a-z0-9_]*$", f"{rel}: bad field name {n!r}")
			if rel not in REPEATED_ALLOWED:
				self.assertEqual(len(names), len(set(names)), f"duplicate DeskField name in {rel}: {names}")
		self.assertGreater(seen, 100)

	def test_every_field_of_an_adopting_form_is_named(self):
		_, unnamed = form_fields.scan()
		for rel, count in unnamed.items():
			self.assertLessEqual(
				count,
				UNNAMED.get(rel, 0),
				f"{rel} has {count} DeskField(s) without a `name` (extensions cannot address them)",
			)

	def test_the_reference_doc_is_current(self):
		doc = (ROOT / "docs" / "extension-sdk-form-fields.md").read_text()
		self.assertEqual(
			doc.rstrip(),
			form_fields.render().rstrip(),
			"run: python frontend/sdk-kit/form_fields.py > docs/extension-sdk-form-fields.md",
		)
