# tests/test_audit.py
import unittest

from sandbox3.audit import run_audit
from sandbox3.cast import Cast
from tests.fakes import FakeLLM
from tests.fixtures import card_zhou, card_shen

GOOD = {"playbook_match": ["第1条"], "playbook_conflict": "无",
        "thought_consistency": "一致", "thought_note": "ok", "fabricated_cues": [],
        "info_overreach": "无", "inner_gap": "无", "verdict": "通过", "note": "ok"}


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.cast = Cast.from_cards([card_zhou(), card_shen()])
        self.kw = dict(actor="周默", internal_thoughts="t", scene={"current_scene": ""},
                       transcript=[], narration="n", juncture="j",
                       visible_ledger=[], hidden_ledger=[],
                       options=[{"id": "A", "text": "x"}],
                       decision={"action_id": "A", "action": "x", "reasoning": "r"})

    def test_passthrough(self):
        a, warns = run_audit(FakeLLM([GOOD]), self.cast, **self.kw)
        self.assertEqual(a["verdict"], "通过")
        self.assertEqual(warns, [])

    def test_bad_verdict_coerced_to_flag(self):
        bad = dict(GOOD, verdict="大概通过")
        a, warns = run_audit(FakeLLM([bad]), self.cast, **self.kw)
        self.assertEqual(a["verdict"], "黄旗")
        self.assertEqual(len(warns), 1)

    def test_hidden_ledger_in_prompt(self):
        fake = FakeLLM([GOOD])
        kw = dict(self.kw, hidden_ledger=[{"time": "t", "text": "秘密事件", "witnesses": ["沈雯"]}])
        run_audit(fake, self.cast, **kw)
        self.assertIn("秘密事件", fake.calls[0][1])     # 范围外块给审计员看（仅供越权对账）


if __name__ == "__main__":
    unittest.main()
