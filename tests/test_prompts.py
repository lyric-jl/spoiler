# tests/test_prompts.py
import unittest

from sandbox3.cast import Cast
from sandbox3.prompts import sm, agent
from sandbox3.states import initial_state
from tests.fixtures import card_zhou, card_shen, card_colleague


class TestPromptGeneralization(unittest.TestCase):
    def setUp(self):
        self.cast2 = Cast.from_cards([card_zhou(), card_shen()])
        self.cast3 = Cast.from_cards([card_zhou(), card_shen(), card_colleague()])

    def test_scene_init_contains_all_members(self):
        tp = {"category": "初来乍到", "title": "t", "sketch": "s", "owner_hints": ""}
        u = sm.scene_init_user(tp, [], initial_state(), self.cast3)
        for name in ("周默", "沈雯", "陈磊"):
            self.assertIn(name, u)
        self.assertIn('"sim_time"', u)

    def test_advance_system_names_others(self):
        s = sm.advance_system(self.cast3)
        self.assertIn("沈雯、陈磊", s)
        self.assertIn("信息防火墙", s)

    def test_settle_has_relations_for_others(self):
        u = sm.settle_user({"theme": "x"}, [], initial_state(), self.cast3)
        self.assertIn('"relations"', u)
        self.assertIn("陈磊", u)
        self.assertIn('"state_changes"', u)   # 差量制保留

    def test_audit_has_four_checks_and_gap(self):
        self.assertIn("信息越权", agent.AUDIT_SYSTEM)
        self.assertIn("心口缝", agent.AUDIT_SYSTEM)
        self.assertIn("只如实记录", agent.AUDIT_SYSTEM)   # 蓝本原文＝"心口缝只如实记录"（test plan 的"只记录"是简写，逐字保真优先）

    def test_decision_schema_unchanged(self):
        u = agent.decision_user("想法", {"current_scene": ""}, [], "n", "j", [],
                                [{"id": "A", "text": "a"}], )
        self.assertIn('"action_id"', u)


if __name__ == "__main__":
    unittest.main()
