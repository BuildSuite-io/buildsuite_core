# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Schedule snapshots — auto-undo for cascading (group) actions + named revisions."""

from frappe.utils import getdate

from buildsuite_core.api import schedule_snapshot as ss
from buildsuite_core.api.schedule_engine import reschedule_downstream
from buildsuite_core.tests.base import BuildSuiteTestCase


class TestScheduleSnapshot(BuildSuiteTestCase):
	def _dated_task(self, project, start, end):
		t = self._make_task(project)
		t.exp_start_date = getdate(start)
		t.exp_end_date = getdate(end)
		t.save(ignore_permissions=True)
		return t

	def _chain(self):
		"""Project with A --FS--> B, so moving A cascades B."""
		p = self._make_project(company=self.company)
		a = self._dated_task(p.name, "2026-01-01", "2026-01-10")
		b = self._dated_task(p.name, "2026-01-11", "2026-01-20")
		b.append("depends_on", {"task": a.name, "dependency_type": "FS", "lag_days": 0})
		b.save(ignore_permissions=True)
		return p, a, b

	def _dates(self, name):
		import frappe

		return frappe.db.get_value("Task", name, ["exp_start_date", "exp_end_date"])

	def test_cascade_captures_undo_and_undo_restores(self):
		p, a, b = self._chain()
		before_a, before_b = self._dates(a.name), self._dates(b.name)

		res = reschedule_downstream(a.name, new_start="2026-01-06", new_end="2026-01-15", dry_run=0)
		self.assertGreaterEqual(len(res["moves"]), 1)  # B cascades downstream

		self.assertEqual(len(ss.list_snapshots(p.name, kind="Undo")), 1)
		self.assertNotEqual(self._dates(b.name), before_b)  # B actually moved

		out = ss.undo_last(p.name)
		self.assertTrue(out["undone"])
		self.assertEqual(self._dates(a.name), before_a)
		self.assertEqual(self._dates(b.name), before_b)
		self.assertEqual(len(ss.list_snapshots(p.name, kind="Undo")), 0)  # popped

	def test_single_task_move_captures_no_undo(self):
		# A move with nothing downstream is not a group action → no undo snapshot.
		p = self._make_project(company=self.company)
		a = self._dated_task(p.name, "2026-01-01", "2026-01-10")
		reschedule_downstream(a.name, new_start="2026-02-01", new_end="2026-02-10", dry_run=0)
		self.assertEqual(len(ss.list_snapshots(p.name, kind="Undo")), 0)

	def test_save_and_restore_revision(self):
		p, a, _b = self._chain()
		baseline = self._dates(a.name)
		rev = ss.save_revision(p.name, "Baseline")["name"]

		a.exp_start_date = getdate("2026-03-01")
		a.exp_end_date = getdate("2026-03-10")
		a.save(ignore_permissions=True)
		self.assertNotEqual(self._dates(a.name), baseline)

		ss.restore_snapshot(rev)
		self.assertEqual(self._dates(a.name), baseline)
		# restoring a revision captures an Undo first, so it's itself undoable
		self.assertGreaterEqual(len(ss.list_snapshots(p.name, kind="Undo")), 1)

	def test_undo_stack_prunes_to_limit(self):
		p, a, _b = self._chain()
		for i in range(ss.UNDO_LIMIT + 3):
			reschedule_downstream(
				a.name,
				new_start=f"2026-01-{6 + i:02d}",
				new_end=f"2026-01-{15 + i:02d}",
				dry_run=0,
			)
		self.assertEqual(len(ss.list_snapshots(p.name, kind="Undo")), ss.UNDO_LIMIT)
