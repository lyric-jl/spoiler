# tests/test_aggregate.py
"""Task 13: 5-run 聚合函数测试（FakeLLM，不跑 live）。
测试策略：跑两局 FakeLLM trace（seed 不同），断言 aggregate() 和 render_aggregate() 行为。"""
import unittest

from sandbox3.cast import Cast
from sandbox3.engine import run_simulation
from sandbox3.scenes import SceneBank
from sandbox3.aggregate import aggregate, render_aggregate
from tests.fakes import FakeLLM
from tests.fixtures import card_zhou, card_shen, router_factory


def _make_trace(seed: int) -> dict:
    """用 FakeLLM 跑一局，返回 trace。router_factory() 有内部状态，每次独立实例化。"""
    cast = Cast.from_cards([card_zhou(), card_shen()])
    bank = SceneBank()
    return run_simulation(cast=cast, llm=FakeLLM(router=router_factory()),
                          bank=bank, n_scenes=1, seed=seed)


class TestAggregate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t1 = _make_trace(42)
        cls.t2 = _make_trace(99)
        cls.traces = [cls.t1, cls.t2]
        cls.agg = aggregate(cls.traces)

    # ── 基础字段 ──────────────────────────────────────────────
    def test_n_runs(self):
        self.assertEqual(self.agg["n_runs"], 2)

    def test_footnote_present(self):
        """脚注含关键诚实口径措辞。"""
        fn = self.agg["footnote"]
        self.assertIn("不构成对真实结局的预测", fn)

    # ── 承诺轨迹按幕对齐 ──────────────────────────────────────
    def test_commitment_trajectory_length(self):
        """幕数=两局最大幕数（均为 1 幕）。"""
        self.assertEqual(len(self.agg["commitment_trajectory"]), 1)

    def test_commitment_trajectory_structure(self):
        c = self.agg["commitment_trajectory"][0]
        self.assertEqual(c["scene"], 1)
        self.assertIsNotNone(c["mean"])
        self.assertIsNotNone(c["min"])
        self.assertIsNotNone(c["max"])
        self.assertGreater(c["n"], 0)

    def test_commitment_mean_in_range(self):
        c = self.agg["commitment_trajectory"][0]
        self.assertGreaterEqual(c["mean"], 0)
        self.assertLessEqual(c["mean"], 5)

    # ── choices 软对齐 ──────────────────────────────────────
    def test_choices_length(self):
        self.assertEqual(len(self.agg["choices"]), 1)

    def test_choices_aligned_true(self):
        """两局同起始 TP（FakeLLM 总返回 C1-01 起始，且只有一幕），对齐标志应为 True。"""
        self.assertTrue(self.agg["choices"][0]["aligned"])

    def test_choices_picks_nonempty(self):
        self.assertGreater(len(self.agg["choices"][0]["picks"]), 0)

    def test_choices_picks_have_run_field(self):
        for p in self.agg["choices"][0]["picks"]:
            self.assertIn("run", p)
            self.assertIn(p["run"], (1, 2))

    # ── vote_stats 累加 ──────────────────────────────────────
    def test_vote_stats_keys(self):
        vs = self.agg["vote_stats"]
        for k in ("全票", "多数票", "摇摆"):
            self.assertIn(k, vs)

    def test_vote_stats_totals_sum_to_beats(self):
        """所有表决之和 == beats_total。"""
        vs = self.agg["vote_stats"]
        total = sum(vs.values())
        self.assertEqual(total, self.agg["beats_total"])

    def test_beats_total_positive(self):
        self.assertGreater(self.agg["beats_total"], 0)

    # ── 状态灯终值 ──────────────────────────────────────────
    def test_final_lights_keys(self):
        from sandbox3.states import STATE_ENUMS
        for k in STATE_ENUMS:
            self.assertIn(k, self.agg["final_lights"])

    def test_final_lights_mode_valid(self):
        from sandbox3.states import STATE_ENUMS
        for k, v in self.agg["final_lights"].items():
            self.assertIn(v["mode"], STATE_ENUMS[k])

    # ── 其他字段存在性 ───────────────────────────────────────
    def test_sway_rate_present(self):
        self.assertIn("sway_rate", self.agg)

    def test_audit_flags_present(self):
        self.assertIn("audit_flags", self.agg)

    def test_inner_gaps_total_nonneg(self):
        self.assertGreaterEqual(self.agg["inner_gaps_total"], 0)


class TestRenderAggregate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t1 = _make_trace(42)
        t2 = _make_trace(99)
        cls.agg = aggregate([t1, t2])
        cls.cfg = {"scenes": 1, "start": "C1-01", "seed": 42}
        cls.rendered = render_aggregate(cls.agg, cls.cfg)

    def test_returns_string(self):
        self.assertIsInstance(self.rendered, str)

    def test_title_present(self):
        self.assertIn("5-run 聚合报告", self.rendered)

    def test_footnote_in_render(self):
        """渲染输出含脚注诚实口径。"""
        self.assertIn("不构成对真实结局的预测", self.rendered)

    def test_commitment_section(self):
        self.assertIn("承诺轨迹", self.rendered)

    def test_final_lights_section(self):
        self.assertIn("状态灯终值", self.rendered)

    def test_vote_section(self):
        self.assertIn("拉扯度", self.rendered)

    def test_choices_section(self):
        self.assertIn("每幕选择并排", self.rendered)


if __name__ == "__main__":
    unittest.main()
