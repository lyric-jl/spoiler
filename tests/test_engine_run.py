# tests/test_engine_run.py
import unittest

from sandbox3.cast import Cast
from sandbox3.engine import run_simulation
from sandbox3.scenes import SceneBank
from tests.fakes import FakeLLM
from tests.fixtures import card_zhou, card_shen

SCENE = {"theme": "t", "sim_time": "入职第1周·周三·上午", "setting": "工位",
         "npc": [], "current_scene": "开场", "goals": {}, "scene_conflict": "冲突"}
ADV1 = {"narration": "推进1", "scene_over": False, "juncture": "节骨眼1", "acting_agent": "周默",
        "options": [{"id": "A", "text": "甲"}, {"id": "B", "text": "乙"}, {"id": "C", "text": "丙"}]}
ADV_OVER = {"narration": "收幕", "scene_over": True}
APPR = {"emotions": {"焦虑": 70}, "internal_thoughts": "心里想着乙"}
DEC_B = {"action_id": "?", "action": "做乙", "reasoning": "符合人设", "confidence": 80,
         "emotion_tags": ["谨慎"]}
AUDIT_OK = {"playbook_match": ["第1条"], "playbook_conflict": "无", "thought_consistency": "一致",
            "thought_note": "", "fabricated_cues": [], "info_overreach": "无",
            "inner_gap": "无", "verdict": "通过", "note": ""}
SETTLE = {"state_changes": {}, "scene_summary": "摘要", "witnesses": ["周默", "沈雯"],
          "relations": {"沈雯": {"attitude": "neutral", "evidence": "证据"}},
          "commitment": 3.0, "commitment_rationale": "理由"}
CONSEQ = {"consequences": []}


def router_factory():
    """按 system 提示词关键词路由 + 决策按'呈现的乙在哪个位置'返回该位（内容恒选乙）。"""
    state = {"adv": 0}
    def router(system, user):
        if "场景主持人" in system and "扩写" in system:
            return dict(SCENE)
        if "节骨眼回合" in system:
            state["adv"] += 1
            return dict(ADV1) if state["adv"] == 1 else dict(ADV_OVER)
        if "情绪评价" in system or "内部情绪" in system:
            return dict(APPR)
        if "面临一个决定" in system:
            # 找到"乙"在本问呈现序中的字母——内容稳定选乙，位置随轮转变
            for line in user.splitlines():
                for label in ("A", "B", "C", "D"):
                    if line.strip().startswith(f"{label}.") and "乙" in line:
                        return dict(DEC_B, action_id=label)
            raise AssertionError("呈现序里找不到乙")
        if "审计员" in system:
            return dict(AUDIT_OK)
        if "收场" in system:
            return dict(SETTLE)
        if "从候选转折点中选出" in system:
            # 控制者增补：plan 嵌入路由缺挑下一幕分支，两幕局必撞——取首个候选 id
            for line in user.splitlines():
                s = line.strip()
                if s.startswith("- "):
                    return {"choice_id": s[2:].split(" ", 1)[0], "why": "测试取首个"}
            return {"choice_id": "?", "why": "测试无候选"}
        if "结算" in system:
            return dict(CONSEQ)
        raise AssertionError(f"未知调用：{system[:50]}")
    return router


class TestRunSimulation(unittest.TestCase):
    def setUp(self):
        self.cast = Cast.from_cards([card_zhou(), card_shen()])
        self.bank = SceneBank()
        self.events = []
        self.trace = run_simulation(cast=self.cast, llm=FakeLLM(router=router_factory()),
                                    bank=self.bank, n_scenes=1, seed=42,
                                    emit=self.events.append)

    def test_call_accounting(self):
        # 搭景1 + 回合(推进1+情绪1+三问3+审计1=6) + 收幕推进1 + 收场1 + 结算1 = 10
        self.assertEqual(self.trace["meta"]["n_llm_calls"], 10)

    def test_unanimous_content_vote_across_orders(self):
        bt = self.trace["scenes"][0]["beats"][0]
        self.assertEqual(bt["vote_summary"]["verdict"], "全票")     # 内容稳定→换序仍全票
        self.assertEqual(bt["decision"]["chosen_orig_id"], "B")
        orders = {tuple(v["order"]) for v in bt["votes"]}
        self.assertEqual(len(orders), 3)                            # 三问顺序确实不同

    def test_ledger_has_time_and_witnesses(self):
        e = self.trace["ledger"][0]
        self.assertEqual(e["time"], "入职第1周·周三·上午")
        self.assertEqual(e["witnesses"], ["周默", "沈雯"])

    def test_relations_validated(self):
        self.assertIn("沈雯", self.trace["scenes"][0]["relations"])

    def test_delta_states_empty_keeps_initial(self):
        self.assertEqual(self.trace["scenes"][0]["state_changes"], {})

    def test_event_stream_types(self):
        types = [e["type"] for e in self.events]
        for t in ("run_started", "scene_open", "beat_open", "inner", "decision",
                  "audit", "settle", "done"):
            self.assertIn(t, types)


class TestFirewallIsolation(unittest.TestCase):
    def test_agent_prompt_excludes_unwitnessed(self):
        """防火墙物理隔离：周默的提示词不得含他不在场的台账条目。"""
        cast = Cast.from_cards([card_zhou(), card_shen()])
        fake = FakeLLM(router=router_factory())
        # 预置台账走不进 run_simulation——改为两幕局：第1幕 witnesses 只有沈雯，第2幕查周默提示词
        settle_private = dict(SETTLE, witnesses=["沈雯"], scene_summary="沈雯单独知道的事")
        state = {"n": 0}
        base = router_factory()
        def router(system, user):
            if "收场" in system:
                state["n"] += 1
                return dict(settle_private) if state["n"] == 1 else dict(SETTLE)
            return base(system, user)
        # 路由的 adv 计数要支持两幕：每幕第1次推进给节骨眼、第2次收幕
        # （base 闭包只数到2，重建一个支持 4 次的：奇数次=ADV1，偶数次=ADV_OVER）
        adv = {"n": 0}
        def router2(system, user):
            if "节骨眼回合" in system:
                adv["n"] += 1
                return dict(ADV1) if adv["n"] % 2 == 1 else dict(ADV_OVER)
            return router(system, user)
        fake = FakeLLM(router=router2)
        run_simulation(cast=cast, llm=fake, bank=SceneBank(), n_scenes=2, seed=1)
        # 第2幕周默侧调用（情绪/决策）的 user 不得出现第1幕私密摘要
        zhou_calls = [u for s, u in fake.calls if "情绪" in s or "面临一个决定" in s]
        second_scene_calls = zhou_calls[1:]          # 第1幕的1次情绪+3次决策之后
        for u in second_scene_calls[4:]:
            self.assertNotIn("沈雯单独知道的事", u)


if __name__ == "__main__":
    unittest.main()
