import unittest

from sandbox3.states import STATE_ENUMS, initial_state, apply_state_deltas, plausible_categories


class TestApplyDeltas(unittest.TestCase):
    def setUp(self):
        self.prev = initial_state()

    def test_empty_delta_keeps_all(self):
        out, ev, warns = apply_state_deltas({}, self.prev)
        self.assertEqual(out, self.prev)
        self.assertEqual(ev, {})
        self.assertEqual(warns, [])

    def test_valid_change_applies_with_evidence(self):
        out, ev, warns = apply_state_deltas(
            {"conflict": {"new": "brewing", "evidence": "当众顶撞"}}, self.prev)
        self.assertEqual(out["conflict"], "brewing")
        self.assertEqual(ev["conflict"], "当众顶撞")
        self.assertEqual(warns, [])

    def test_unknown_light_rejected(self):
        out, ev, warns = apply_state_deltas({"mood": {"new": "bad"}}, self.prev)
        self.assertEqual(out, self.prev)
        self.assertEqual(len(warns), 1)

    def test_out_of_enum_rejected(self):
        out, ev, warns = apply_state_deltas({"conflict": {"new": "爆炸"}}, self.prev)
        self.assertEqual(out["conflict"], self.prev["conflict"])
        self.assertEqual(len(warns), 1)

    def test_downgrade_to_unknown_rejected(self):
        prev = dict(self.prev, conflict="brewing")
        out, ev, warns = apply_state_deltas({"conflict": {"new": "unknown"}}, prev)
        self.assertEqual(out["conflict"], "brewing")
        self.assertEqual(len(warns), 1)

    def test_noop_same_value_silently_skipped(self):
        out, ev, warns = apply_state_deltas({"conflict": {"new": "none"}}, self.prev)
        self.assertEqual(out, self.prev)
        self.assertEqual(ev, {})
        self.assertEqual(warns, [])


class TestHeuristic(unittest.TestCase):
    def test_initial_first_scene(self):
        # role_clarity=unclear → 必含 磨合建制
        self.assertIn("磨合建制", plausible_categories(initial_state(), 1))


if __name__ == "__main__":
    unittest.main()
