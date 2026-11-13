"""Every DeskSection with an `id` is an extension anchor (form.<DocType>.before|after.<id>), so the
ids are public: they must stay unique within a file and URL/slot safe."""

import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
TAG = re.compile(r"<DeskSection\b([^>]*)>", re.S)


class TestSectionIds(unittest.TestCase):
	def test_ids_are_unique_per_file_and_slot_safe(self):
		seen = 0
		for path in SRC.rglob("*.vue"):
			ids = [
				m.group(1)
				for t in TAG.findall(path.read_text())
				if (m := re.search(r'(?<![:\w-])id="([^"]+)"', t))
			]
			seen += len(ids)
			self.assertEqual(len(ids), len(set(ids)), f"duplicate DeskSection id in {path.name}: {ids}")
			for i in ids:
				self.assertRegex(i, r"^[a-z0-9][a-z0-9-]*$", f"{path.name}: bad id {i!r}")
		self.assertGreater(seen, 100)  # the pass over the views is in place
