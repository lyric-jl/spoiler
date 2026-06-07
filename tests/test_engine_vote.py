# tests/test_engine_vote.py
import random
import unittest

from sandbox3.engine import _build_presentations, _tally_votes

OPTS = [{"id": "A", "text": "甲"}, {"id": "B", "text": "乙"}, {"id": "C", "text": "丙"}]


class TestPresentations(unittest.TestCase):
    def test_three_distinct_rotations(self):
        rounds = _build_presentations(OPTS, random.Random(42))
        self.assertEqual(len(rounds), 3)
        orders = [tuple(o["orig_id"] for o in r) for r in rounds]
        self.assertEqual(len(set(orders)), 3)            # 三问顺序互不相同
        for r in rounds:
            self.assertEqual([o["id"] for o in r], ["A", "B", "C"])  # 呈现位重发 ABC

    def test_each_option_leads_once(self):
        rounds = _build_presentations(OPTS, random.Random(7))
        firsts = {r[0]["orig_id"] for r in rounds}
        self.assertEqual(len(firsts), 3)                 # 每个选项各坐一次头排


class TestTally(unittest.TestCase):
    def _vote(self, rnd, orig):
        return {"round": rnd, "orig_id": orig, "position": "A", "reasoning": "", "confidence": 80}

    def test_majority(self):
        votes = [self._vote(1, "B"), self._vote(2, "A"), self._vote(3, "B")]
        s = _tally_votes(votes)
        self.assertEqual((s["verdict"], s["winner_orig_id"], s["winner_round"]), ("多数票", "B", 1))

    def test_unanimous(self):
        votes = [self._vote(i, "C") for i in (1, 2, 3)]
        self.assertEqual(_tally_votes(votes)["verdict"], "全票")

    def test_sway_takes_round1(self):
        votes = [self._vote(1, "A"), self._vote(2, "B"), self._vote(3, "C")]
        s = _tally_votes(votes)
        self.assertEqual((s["verdict"], s["winner_orig_id"]), ("摇摆", "A"))


if __name__ == "__main__":
    unittest.main()
