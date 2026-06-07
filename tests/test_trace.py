# tests/test_trace.py
"""台本渲染 + run 落盘测试。"""
import tempfile
import pathlib
import unittest

from sandbox3.engine import run_simulation
from sandbox3.cast import Cast
from sandbox3.scenes import SceneBank
from sandbox3.trace import render, save_run
from tests.fakes import FakeLLM
from tests.fixtures import (card_zhou, card_shen, card_colleague,
                             router_factory)


def _make_trace():
    cast = Cast.from_cards([card_zhou(), card_shen()])
    bank = SceneBank()
    return run_simulation(cast=cast, llm=FakeLLM(router=router_factory()),
                          bank=bank, n_scenes=1, seed=42)


class TestRender(unittest.TestCase):
    def setUp(self):
        self.trace = _make_trace()
        self.md = render(self.trace)

    # ---- 换序三问表决（蓝本原文子串）----
    def test_contains_vote_verdict(self):
        self.assertIn("换序三问表决", self.md)

    # ---- 心口缝（蓝本原文子串）----
    def test_contains_inner_gap(self):
        self.assertIn("心口缝（只记录不打分）", self.md)

    # ---- 时间/在场（蓝本已有，保留验证）----
    def test_contains_sim_time_header(self):
        self.assertIn("**时间**", self.md)

    # ---- 关系细目（v3 新增段落）----
    def test_contains_relations_section(self):
        self.assertIn("关系细目", self.md)

    # ---- 脚注核心口径句 ----
    def test_contains_prediction_disclaimer(self):
        self.assertIn("不构成对真实结局的预测", self.md)

    # ---- v3 新增：人设可为蒸馏产物 ----
    def test_contains_distillation_note(self):
        self.assertIn("人设可为蒸馏产物", self.md)

    # ---- 候选人名在观察主体行 ----
    def test_candidate_in_header(self):
        self.assertIn("周默", self.md)

    # ---- cast 列表（kind=candidate/counterpart 应出现在头部）----
    def test_cast_listed_in_header(self):
        # 头部应列出 cast 成员与 kind
        self.assertIn("在场名单：", self.md)
        self.assertIn("沈雯（counterpart）", self.md)

    # ---- 审计只标记不改判（脚注）----
    def test_audit_disclaimer_present(self):
        self.assertIn("理由审计员也是 AI", self.md)


class TestSaveRun(unittest.TestCase):
    def test_save_run_produces_two_files(self):
        trace = _make_trace()
        with tempfile.TemporaryDirectory() as tmp:
            out = save_run(trace, out_root=pathlib.Path(tmp))
            self.assertTrue((out / "trace.json").exists())
            self.assertTrue((out / "台本.md").exists())

    def test_save_run_with_jd_produces_three_files(self):
        trace = _make_trace()
        with tempfile.TemporaryDirectory() as tmp:
            out = save_run(trace, out_root=pathlib.Path(tmp), jd="某 JD 描述")
            self.assertTrue((out / "trace.json").exists())
            self.assertTrue((out / "台本.md").exists())
            self.assertTrue((out / "jd.txt").exists())

    def test_trace_json_is_valid(self):
        import json
        trace = _make_trace()
        with tempfile.TemporaryDirectory() as tmp:
            out = save_run(trace, out_root=pathlib.Path(tmp))
            loaded = json.loads((out / "trace.json").read_text(encoding="utf-8"))
            self.assertIn("meta", loaded)
            self.assertIn("scenes", loaded)


class TestRenderDegraded(unittest.TestCase):
    """缺字段降级路径：render 不炸、降级提示到位。"""

    # 最小 meta（无 cast 键）+ 最小 scenes（空列表）
    _MINIMAL_META_NO_CAST = {
        "model": "fake", "n_scenes": 0, "n_llm_calls": 0, "warnings_total": 0,
        "actor_counts": {}, "audit_flags": 0, "seed": 0,
        "vote_stats": {}, "vote_position_counts": {}, "inner_gaps": {},
        "candidate": "测试候选人",
        # 故意不包含 "cast" 键
    }

    def test_meta_without_cast(self):
        """meta 无 cast 键时 render 不报错，头部含降级提示。"""
        trace = {"meta": dict(self._MINIMAL_META_NO_CAST), "scenes": []}
        md = render(trace)
        self.assertIn("（无在场名单信息）", md)

    def test_scene_without_relations(self):
        """某幕 relations 为空/缺失时 render 不报错，且该幕无"关系细目"段。"""
        from sandbox3.states import STATE_ENUMS
        # 取一条真实 trace，把第一幕 relations 清空
        trace = _make_trace()
        scene0 = trace["scenes"][0]
        scene0["relations"] = {}  # 置空
        md = render(trace)
        # render 不应抛异常（能到这里就算通过），全文结构正常
        self.assertIn("承诺轨迹", md)
        # 若所有幕均无 relations，则"关系细目"不应出现
        all_empty = all(not sc.get("relations") for sc in trace["scenes"])
        if all_empty:
            self.assertNotIn("关系细目", md)


if __name__ == "__main__":
    unittest.main()
