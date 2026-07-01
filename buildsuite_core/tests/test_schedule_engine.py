# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt
"""Pure-function tests for the scheduling engine (conflict flagging + cascade).

These are the SHARED TEST VECTORS: the frontend `useScheduleEngine` port must
produce identical results for the same inputs, so the client preview and the
server's authoritative commit never disagree.
"""

from datetime import date

import frappe
from frappe.tests import UnitTestCase

from buildsuite_core.api import schedule_engine as eng
from buildsuite_core.tests.base import BuildSuiteTestCase


def _t(name, type="Activity", start=None, end=None, status="Open"):
	return {"name": name, "type": type, "start": start, "end": end, "status": status}


def _e(pred, succ, type="FS", lag=0):
	return {"predecessor": pred, "successor": succ, "type": type, "lag": lag}


class TestScheduleEngine(UnitTestCase):
	def test_fs_conflict_flagged(self):
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 10)),
			"B": _t("B", start=date(2026, 1, 5), end=date(2026, 1, 15)),  # starts before A ends
		}
		res = eng.compute_conflicts("A", tasks, [_e("A", "B")])
		self.assertTrue(res["B"][0])
		self.assertIn("earlier than allowed", res["B"][1])
		self.assertFalse(res["A"][0])

	def test_fs_satisfied_no_conflict(self):
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 10)),
			"B": _t("B", start=date(2026, 1, 11), end=date(2026, 1, 20)),
		}
		res = eng.compute_conflicts("A", tasks, [_e("A", "B")])
		self.assertFalse(res["B"][0])

	def test_cascade_shifts_duration_preserving(self):
		# B (10-day span) FS-depends on A. FS earliest = pred end + lag (same-day start
		# allowed, per the locked prototype convention). Move A to end 01-20 -> B
		# starts 01-20, ends 01-30.
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 10)),
			"B": _t("B", start=date(2026, 1, 11), end=date(2026, 1, 21)),
		}
		moves = eng.compute_cascade(
			"A", tasks, [_e("A", "B")], {"start": date(2026, 1, 11), "end": date(2026, 1, 20)}
		)
		self.assertEqual(len(moves), 1)
		self.assertEqual(moves[0]["task"], "B")
		self.assertEqual(moves[0]["new_start"], "2026-01-20")
		self.assertEqual(moves[0]["new_end"], "2026-01-30")

	def test_cascade_no_pull_earlier(self):
		# B already far later than A's end -> cascade leaves it untouched.
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 10)),
			"B": _t("B", start=date(2026, 2, 1), end=date(2026, 2, 10)),
		}
		moves = eng.compute_cascade(
			"A", tasks, [_e("A", "B")], {"start": date(2026, 1, 3), "end": date(2026, 1, 12)}
		)
		self.assertEqual(moves, [])

	def test_milestone_successor_single_date(self):
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 10)),
			"M": _t("M", type="Milestone", start=None, end=date(2026, 1, 5)),  # due before A ends
		}
		edges = [_e("A", "M")]
		res = eng.compute_conflicts("A", tasks, edges)
		self.assertTrue(res["M"][0])
		self.assertIn("Due", res["M"][1])
		moves = eng.compute_cascade("A", tasks, edges)
		self.assertEqual(len(moves), 1)
		self.assertTrue(moves[0]["is_milestone"])
		self.assertEqual(moves[0]["new_end"], "2026-01-10")
		self.assertIsNone(moves[0]["new_start"])

	def test_inspection_gate_blocks_successor(self):
		tasks = {
			"I": _t("I", type="Inspection", start=date(2026, 1, 1), end=date(2026, 1, 2), status="Working"),
			"B": _t("B", start=date(2026, 1, 10), end=date(2026, 1, 20)),  # dates fine, but gate open
		}
		res = eng.compute_conflicts("I", tasks, [_e("I", "B")])
		self.assertTrue(res["B"][0])
		self.assertIn("Waiting on inspection I", res["B"][1])

	def test_completed_inspection_does_not_block(self):
		tasks = {
			"I": _t("I", type="Inspection", start=date(2026, 1, 1), end=date(2026, 1, 2), status="Completed"),
			"B": _t("B", start=date(2026, 1, 10), end=date(2026, 1, 20)),
		}
		res = eng.compute_conflicts("I", tasks, [_e("I", "B")])
		self.assertFalse(res["B"][0])

	def test_cycle_aborts_cascade(self):
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 5)),
			"B": _t("B", start=date(2026, 1, 6), end=date(2026, 1, 10)),
		}
		self.assertIsNone(eng.compute_cascade("A", tasks, [_e("A", "B"), _e("B", "A")]))

	def test_multi_predecessor_takes_most_binding(self):
		# B depends FS on A (ends 01-10) and SS on C (starts 01-20). Most binding = 01-21.
		tasks = {
			"A": _t("A", start=date(2026, 1, 1), end=date(2026, 1, 10)),
			"C": _t("C", start=date(2026, 1, 20), end=date(2026, 1, 25)),
			"B": _t("B", start=date(2026, 1, 5), end=date(2026, 1, 15)),
		}
		edges = [_e("A", "B", "FS"), _e("C", "B", "SS", 1)]
		earliest, reason = eng._compute_earliest_start("B", tasks, edges)
		self.assertEqual(earliest, date(2026, 1, 21))
		self.assertIn("from C", reason)


class TestScheduleEngineIntegration(BuildSuiteTestCase):
	"""End-to-end over the DB: the on_update hook flags conflicts, and
	reschedule_downstream previews + commits a cascade."""

	def _task(self, project, subject, start, end, type="Activity"):
		return frappe.get_doc(
			{
				"doctype": "Task",
				"project": project,
				"subject": subject,
				"type": type,
				"exp_start_date": start,
				"exp_end_date": end,
			}
		).insert(ignore_permissions=True)

	def test_hook_flags_then_cascade_clears(self):
		p = self._make_project(company=self.company)
		a = self._task(p.name, f"A {self._n}", "2026-01-01", "2026-01-10")
		b = self._task(p.name, f"B {self._n}", "2026-01-05", "2026-01-15")  # starts before A ends

		# Adding the FS edge + saving B fires the on_update recompute hook.
		b.append("depends_on", {"task": a.name, "dependency_type": "FS", "lag_days": 0})
		b.save(ignore_permissions=True)
		b.reload()
		self.assertTrue(b.schedule_conflict)
		self.assertIn("earlier than allowed", b.conflict_reason or "")

		# Dry-run cascade: moving A's end to 01-20 should propose moving B.
		preview = eng.reschedule_downstream(a.name, new_start="2026-01-01", new_end="2026-01-20", dry_run=1)
		self.assertEqual([m["task"] for m in preview["moves"]], [b.name])

		# Commit: B shifts (duration-preserving) and its conflict clears.
		eng.reschedule_downstream(a.name, new_start="2026-01-01", new_end="2026-01-20", dry_run=0)
		b.reload()
		self.assertEqual(str(b.exp_start_date)[:10], "2026-01-20")
		self.assertFalse(b.schedule_conflict)
