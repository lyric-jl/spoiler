# tests/test_engine_run.py
import unittest

from sandbox3.cast import Cast
from sandbox3.engine import run_simulation
from sandbox3.scenes import SceneBank
from tests.fakes import FakeLLM
from tests.fixtures import (card_zhou, card_shen, card_colleague,
                             router_factory, ADV1, ADV_OVER, APPR, DEC_B,
                             AUDIT_OK, SETTLE, CONSEQ)


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


class TestRelationsFiltering(unittest.TestCase):
    """relations 三条过滤分支的负路径测试（三人局：周默/沈雯/陈磊）。"""

    def setUp(self):
        # 三人局：候选人=周默，counterpart=沈雯，colleague=陈磊
        self.cast = Cast.from_cards([card_zhou(), card_shen(), card_colleague()])
        self.bank = SceneBank()

        # settle 含四条 relations，覆盖三条过滤分支
        settle_filter = dict(SETTLE, relations={
            "沈雯":  {"attitude": "supportive", "evidence": "e1"},  # 合法 → 应保留
            "陈磊":  {"attitude": "敌对",       "evidence": "e2"},  # attitude 越界 → 整条丢弃
            "周默":  {"attitude": "neutral",    "evidence": "e3"},  # 候选人自指 → 丢弃
            "路人甲": {"attitude": "neutral",   "evidence": "e4"},  # 名单外 → 丢弃
        })

        def router(system, user):
            if "收场" in system:
                return dict(settle_filter)
            return router_factory()(system, user)

        # router_factory 内部有状态，需独立实例处理 adv 计数
        base = router_factory()
        def router2(system, user):
            if "收场" in system:
                return dict(settle_filter)
            return base(system, user)

        self.trace = run_simulation(
            cast=self.cast,
            llm=FakeLLM(router=router2),
            bank=self.bank,
            n_scenes=1,
            seed=42,
        )

    def test_valid_relation_kept(self):
        """attitude 合法的 counterpart 应保留在 relations。"""
        rels = self.trace["scenes"][0]["relations"]
        self.assertIn("沈雯", rels)
        self.assertEqual(rels["沈雯"]["attitude"], "supportive")

    def test_candidate_self_reference_dropped(self):
        """候选人自指（周默）应被剔除，不得出现在 relations。"""
        rels = self.trace["scenes"][0]["relations"]
        self.assertNotIn("周默", rels)

    def test_out_of_cast_dropped(self):
        """名单外名字（路人甲）应被剔除。"""
        rels = self.trace["scenes"][0]["relations"]
        self.assertNotIn("路人甲", rels)

    def test_invalid_attitude_dropped(self):
        """attitude 越界（"敌对"不在枚举）→ 整条丢弃，陈磊不得出现在 relations。
        引擎行 259-261：attitude not in (supportive/neutral/opposed) → 整条过滤掉，不做矫正。"""
        rels = self.trace["scenes"][0]["relations"]
        self.assertNotIn("陈磊", rels)


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


class TestThreePersonRun(unittest.TestCase):
    """P1 三人局（周默/沈雯/陈磊）集成测试——三回合各行动一次，FakeLLM 不花钱。"""

    # settle 含沈雯+陈磊两条合法 relations
    SETTLE_THREE = dict(SETTLE, witnesses=["周默", "沈雯", "陈磊"],
                        relations={
                            "沈雯": {"attitude": "neutral",    "evidence": "沈雯证据"},
                            "陈磊": {"attitude": "supportive", "evidence": "陈磊证据"},
                        })

    @staticmethod
    def _make_router():
        """三回合 advance：周默→陈磊→沈雯，第4次 scene_over。"""
        adv_seq = [
            dict(ADV1, acting_agent="周默"),
            dict(ADV1, acting_agent="陈磊"),
            dict(ADV1, acting_agent="沈雯"),
            dict(ADV_OVER),                     # 第4次收幕
        ]
        idx = {"n": 0}
        base = router_factory()

        def router(system, user):
            if "节骨眼回合" in system:
                i = idx["n"]
                idx["n"] += 1
                return dict(adv_seq[i])
            if "收场" in system:
                return dict(TestThreePersonRun.SETTLE_THREE)
            return base(system, user)

        return router

    def setUp(self):
        self.cast = Cast.from_cards([card_zhou(), card_shen(), card_colleague()])
        self.bank = SceneBank()
        self.fake = FakeLLM(router=self._make_router())
        self.trace = run_simulation(
            cast=self.cast, llm=self.fake, bank=self.bank, n_scenes=1, seed=42)

    # ---- 断言 1：三人各行动 1 次 ----
    def test_actor_counts_all_three(self):
        ac = self.trace["meta"]["actor_counts"]
        self.assertEqual(ac.get("周默"), 1, f"周默应行动1次，实际：{ac}")
        self.assertEqual(ac.get("陈磊"), 1, f"陈磊应行动1次，实际：{ac}")
        self.assertEqual(ac.get("沈雯"), 1, f"沈雯应行动1次，实际：{ac}")

    # ---- 断言 2：陈磊作为行动方时 beat 三件齐（appraisal/votes/audit）----
    def test_chen_lei_beat_has_full_pipeline(self):
        beats = self.trace["scenes"][0]["beats"]
        chen_beats = [b for b in beats if b["acting_agent"] == "陈磊"]
        self.assertEqual(len(chen_beats), 1, "陈磊应有且仅有1个 beat")
        b = chen_beats[0]
        self.assertIn("appraisal", b, "陈磊 beat 缺 appraisal")
        self.assertIn("votes",     b, "陈磊 beat 缺 votes")
        self.assertIn("audit",     b, "陈磊 beat 缺 audit")
        # 进一步确认各件非空
        self.assertTrue(b["votes"],     "陈磊 beat 的 votes 不应为空")
        self.assertIn("verdict", b["audit"], "陈磊 beat 的 audit 缺 verdict")

    # ---- 断言 3：settle 的 relations 含沈雯+陈磊两条 ----
    def test_settle_relations_shen_and_chen(self):
        rels = self.trace["scenes"][0]["relations"]
        self.assertIn("沈雯", rels, f"relations 应含沈雯，实际：{list(rels)}")
        self.assertIn("陈磊", rels, f"relations 应含陈磊，实际：{list(rels)}")
        self.assertNotIn("周默", rels, "候选人周默不应出现在 relations")

    # ---- 断言 4：防火墙——只有沈雯+陈磊在场的台账不进周默的提示词 ----
    def test_firewall_zhou_cannot_see_shen_chen_only_entry(self):
        """两幕局：第1幕 witnesses 只含沈雯+陈磊（周默不在场），
        第2幕周默作为行动方时的 appraisal/decision user 串不应包含第1幕的私密摘要。"""
        private_summary = "陈磊和沈雯单独商量的事_仅两人知道"
        settle_private = dict(self.SETTLE_THREE,
                              witnesses=["沈雯", "陈磊"],
                              scene_summary=private_summary)

        adv_seq = [
            # 第1幕：陈磊行动1次后收幕（周默不作为行动方，防止他那幕的 appraisal user 干扰）
            dict(ADV1, acting_agent="陈磊"),
            dict(ADV_OVER),
            # 第2幕：周默行动1次后收幕
            dict(ADV1, acting_agent="周默"),
            dict(ADV_OVER),
        ]
        idx2 = {"n": 0, "settle": 0}
        base2 = router_factory()

        def router2(system, user):
            if "节骨眼回合" in system:
                i = idx2["n"]
                idx2["n"] += 1
                return dict(adv_seq[i])
            if "收场" in system:
                idx2["settle"] += 1
                return dict(settle_private) if idx2["settle"] == 1 else dict(self.SETTLE_THREE)
            return base2(system, user)

        fake2 = FakeLLM(router=router2)
        run_simulation(cast=self.cast, llm=fake2, bank=SceneBank(), n_scenes=2, seed=7)

        # 第2幕中周默作为行动方的 appraisal + decision user 串不得含私密摘要
        zhou_appr_dec_calls = [
            u for s, u in fake2.calls
            if ("情绪评价" in s or "内部情绪" in s or "面临一个决定" in s)
            and "周默" in s   # appraisal_system / decision_system 含 persona_block → 含"周默"
        ]
        # 第1幕陈磊作为行动方，所以周默的 appraisal/decision 全部属于第2幕
        self.assertTrue(zhou_appr_dec_calls, "未捕获到周默作为行动方的 appraisal/decision 调用")
        for u in zhou_appr_dec_calls:
            self.assertNotIn(private_summary, u,
                             "防火墙漏洞：周默的提示词中出现了他不在场的私密台账条目")


if __name__ == "__main__":
    unittest.main()
