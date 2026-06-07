# tests/test_tools.py
"""tools/ 体检工具测试：checkup（位置偏置）+ leakcheck（防火墙）。

构造最小 trace dict 进行单元测试，不依赖 LLM 或真实 run 目录。
"""
import json
import pathlib
import tempfile
import unittest

# ---- 辅助：构造最小 trace ----------------------------------------

def _make_beat(beat_no: int, actor: str, internal_thoughts: str,
               reasoning: str, action: str,
               votes: list[dict], winner_orig_id: str) -> dict:
    """构造一个最小 beat dict，字段名与 engine.py 实际产出一致。"""
    return {
        "beat": beat_no,
        "narration": f"回合{beat_no}叙事",
        "juncture": "节骨眼",
        "acting_agent": actor,
        "options": [{"id": "A", "text": "甲", "orig_id": "A"},
                    {"id": "B", "text": "乙", "orig_id": "B"},
                    {"id": "C", "text": "丙", "orig_id": "C"}],
        "options_original": [{"id": "A", "text": "甲"},
                              {"id": "B", "text": "乙"},
                              {"id": "C", "text": "丙"}],
        "appraisal": {"internal_thoughts": internal_thoughts, "emotions": {}},
        "votes": votes,
        "vote_summary": {
            "rounds": len(votes),
            "tally": {},
            "verdict": "全票",
            "winner_orig_id": winner_orig_id,
            "winner_round": 1,
        },
        "decision": {"action_id": "A", "action": action,
                     "reasoning": reasoning, "confidence": 80,
                     "chosen_orig_id": winner_orig_id},
        "audit": {"verdict": "通过", "inner_gap": "无"},
        "warnings": [],
    }


def _vote(rnd: int, position: str, orig_id: str, reasoning: str = "") -> dict:
    return {"round": rnd, "order": ["A", "B", "C"], "position": position,
            "orig_id": orig_id, "reasoning": reasoning, "confidence": 80}


def _make_trace(scenes: list[dict]) -> dict:
    return {
        "meta": {"model": "fake", "n_scenes": len(scenes), "n_llm_calls": 0,
                 "seed": 0, "candidate": "周默",
                 "vote_stats": {}, "vote_position_counts": {},
                 "actor_counts": {}, "audit_flags": 0, "inner_gaps": {},
                 "warnings_total": 0},
        "final_state": {},
        "ledger": [],
        "scenes": scenes,
    }


# ==================================================================
# checkup 测试
# ==================================================================

class TestCheckupFunction(unittest.TestCase):
    """checkup(run_dirs) -> dict 单元测试。"""

    def _make_run_dir(self, trace: dict) -> pathlib.Path:
        tmp = tempfile.mkdtemp()
        p = pathlib.Path(tmp)
        (p / "trace.json").write_text(
            json.dumps(trace, ensure_ascii=False), encoding="utf-8")
        return p

    def _balanced_votes(self) -> list:
        """3 问各用不同呈现位，orig_id 恒为 A——模拟三问轮转、winner 在三个坑位各出现一次。"""
        return [_vote(1, "A", "A"), _vote(2, "B", "A"), _vote(3, "C", "A")]

    def test_vote_position_counts_correct(self):
        """统计每个呈现位被选中的次数正确（3 问×1 beat，各位 1 次）。"""
        from sandbox3.tools.checkup import checkup
        beat = _make_beat(1, "周默", "内心", "理由", "行动",
                          votes=self._balanced_votes(), winner_orig_id="A")
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        run_dir = self._make_run_dir(trace)
        result = checkup([run_dir])
        counts = result["position_counts"]
        self.assertEqual(counts.get("A", 0), 1)
        self.assertEqual(counts.get("B", 0), 1)
        self.assertEqual(counts.get("C", 0), 1)

    def test_winner_position_a_ratio(self):
        """winner_orig_id 对应的第1问呈现位 A 占比计算正确。

        构造：2 个 beat，winner 在第1问的呈现位均为 A
        → winner_pos_a_ratio = 2/2 = 1.0（此例故意偏，测算法正确性）。
        """
        from sandbox3.tools.checkup import checkup
        votes1 = [_vote(1, "A", "X"), _vote(2, "B", "Y"), _vote(3, "C", "X")]
        votes2 = [_vote(1, "A", "Z"), _vote(2, "C", "W"), _vote(3, "B", "Z")]
        beat1 = _make_beat(1, "周默", "", "", "", votes=votes1, winner_orig_id="X")
        beat2 = _make_beat(2, "周默", "", "", "", votes=votes2, winner_orig_id="Z")
        # beat1: winner X 第1问在 A 位 → 计 A
        # beat2: winner Z 第1问在 A 位 → 计 A
        scene = {"index": 1, "beats": [beat1, beat2]}
        trace = _make_trace([scene])
        run_dir = self._make_run_dir(trace)
        result = checkup([run_dir])
        self.assertAlmostEqual(result["winner_pos_a_ratio"], 1.0)

    def test_pass_verdict_near_third(self):
        """winner 呈现位 A 占比 ≈1/3 时判语为过。

        构造 3 个 beat，winner 第1问呈现位分别为 A/B/C → ratio=1/3。
        """
        from sandbox3.tools.checkup import checkup
        # beat1: winner orig=X，第1问在 A 位
        b1 = _make_beat(1, "周默", "", "", "",
                        votes=[_vote(1, "A", "X"), _vote(2, "B", "X"), _vote(3, "C", "X")],
                        winner_orig_id="X")
        # beat2: winner orig=Y，第1问在 B 位
        b2 = _make_beat(2, "周默", "", "", "",
                        votes=[_vote(1, "B", "Y"), _vote(2, "C", "Y"), _vote(3, "A", "Y")],
                        winner_orig_id="Y")
        # beat3: winner orig=Z，第1问在 C 位
        b3 = _make_beat(3, "周默", "", "", "",
                        votes=[_vote(1, "C", "Z"), _vote(2, "A", "Z"), _vote(3, "B", "Z")],
                        winner_orig_id="Z")
        scene = {"index": 1, "beats": [b1, b2, b3]}
        trace = _make_trace([scene])
        run_dir = self._make_run_dir(trace)
        result = checkup([run_dir])
        self.assertAlmostEqual(result["winner_pos_a_ratio"], 1 / 3, places=5)
        self.assertIn("pass", result["verdict"].lower(),
                      msg=f"期望 pass 判语，实际: {result['verdict']}")

    def test_fail_verdict_biased(self):
        """winner 呈现位 A 占比过高（100%）时判语含 fail 或偏置警告。"""
        from sandbox3.tools.checkup import checkup
        beats = []
        for i in range(3):
            beats.append(_make_beat(
                i + 1, "周默", "", "", "",
                votes=[_vote(1, "A", f"X{i}"), _vote(2, "B", f"X{i}"), _vote(3, "C", f"X{i}")],
                winner_orig_id=f"X{i}",
            ))
        scene = {"index": 1, "beats": beats}
        trace = _make_trace([scene])
        run_dir = self._make_run_dir(trace)
        result = checkup([run_dir])
        self.assertAlmostEqual(result["winner_pos_a_ratio"], 1.0)
        self.assertNotIn("pass", result["verdict"].lower(),
                         msg=f"偏置情形不应判 pass，实际: {result['verdict']}")

    def test_total_beats_count(self):
        """total_beats 计数正确（跨 run_dir 累加）。"""
        from sandbox3.tools.checkup import checkup
        beat = _make_beat(1, "周默", "", "", "",
                          votes=[_vote(1, "A", "A")], winner_orig_id="A")
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        d1 = self._make_run_dir(trace)
        d2 = self._make_run_dir(trace)
        result = checkup([d1, d2])
        self.assertEqual(result["total_beats"], 2)


# ==================================================================
# leakcheck 测试
# ==================================================================

class TestLeakcheckFunction(unittest.TestCase):
    """leakcheck(trace, actor, keywords) -> dict 单元测试。"""

    def _clean_beat(self) -> dict:
        """周默 beat，内心/理由/行动均不含关键词。"""
        return _make_beat(1, "周默", "心里想着要好好表现", "工作努力", "按时提交",
                          votes=[_vote(1, "A", "A", reasoning="没有特殊想法")],
                          winner_orig_id="A")

    def _leaky_beat(self) -> dict:
        """周默 beat，内心 reasoning 里含关键词"编制"。"""
        return _make_beat(2, "周默", "心里想着编制问题会影响我留下来吗", "担心",
                          "继续观望",
                          votes=[_vote(1, "A", "A",
                                       reasoning="我知道编制在收紧，所以选保守方案")],
                          winner_orig_id="A")

    def test_no_leak_clean_beat(self):
        """干净 beat 无命中。"""
        from sandbox3.tools.leakcheck import leakcheck
        beat = self._clean_beat()
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制", "合并", "缩编"])
        self.assertEqual(result["hit_count"], 0)
        self.assertEqual(len(result["hits"]), 0)

    def test_leak_in_internal_thoughts(self):
        """内心含关键词时命中 1 处。"""
        from sandbox3.tools.leakcheck import leakcheck
        beat = _make_beat(1, "周默",
                          internal_thoughts="心里想着编制问题",
                          reasoning="正常理由", action="正常行动",
                          votes=[_vote(1, "A", "A")], winner_orig_id="A")
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制"])
        self.assertGreaterEqual(result["hit_count"], 1)
        labels = [h["label"] for h in result["hits"]]
        self.assertTrue(any("内心" in lb for lb in labels),
                        msg=f"期望内心命中，实际标签: {labels}")

    def test_leak_in_vote_reasoning(self):
        """换序三问 reasoning 含关键词时命中。"""
        from sandbox3.tools.leakcheck import leakcheck
        votes = [_vote(1, "A", "A", reasoning="知道编制要收紧所以谨慎")]
        beat = _make_beat(1, "周默", "普通内心", "普通理由", "普通行动",
                          votes=votes, winner_orig_id="A")
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制"])
        self.assertGreaterEqual(result["hit_count"], 1)
        labels = [h["label"] for h in result["hits"]]
        self.assertTrue(any("投票" in lb or "第1问" in lb for lb in labels),
                        msg=f"期望投票理由命中，实际标签: {labels}")

    def test_two_leaky_beats_hit_count(self):
        """两个都有泄漏的 beat，命中数 >= 2（每 beat 至少 1 处）。"""
        from sandbox3.tools.leakcheck import leakcheck
        b1 = self._clean_beat()
        b2 = self._leaky_beat()   # 内心 + 投票理由各含关键词
        scene = {"index": 1, "beats": [b1, b2]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制", "合并", "缩编"])
        self.assertGreaterEqual(result["hit_count"], 2,
                                msg=f"期望 >=2 命中，实际 {result['hit_count']}")

    def test_other_actor_internal_thoughts_ignored(self):
        """非目标 actor（沈雯）的内心不计入 hits，计入 ok_mentions。"""
        from sandbox3.tools.leakcheck import leakcheck
        beat = _make_beat(1, "沈雯",
                          internal_thoughts="编制收紧，我不打算告诉下面的人",
                          reasoning="正常", action="正常",
                          votes=[_vote(1, "A", "A")], winner_orig_id="A")
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制"])
        self.assertEqual(result["hit_count"], 0)
        self.assertGreaterEqual(len(result["ok_mentions"]), 1,
                                msg="沈雯内心含关键词应记 ok_mentions")

    def test_narration_cognitive_pattern_detected(self):
        """叙事中'周默心想…编制'句式命中。"""
        from sandbox3.tools.leakcheck import leakcheck
        beat = _make_beat(1, "周默", "普通内心", "普通理由", "普通行动",
                          votes=[_vote(1, "A", "A")], winner_orig_id="A")
        beat["narration"] = "周默心想着编制的事会不会影响自己。"
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制"])
        self.assertGreaterEqual(result["hit_count"], 1)
        labels = [h["label"] for h in result["hits"]]
        self.assertTrue(any("叙事" in lb for lb in labels),
                        msg=f"期望叙事认知句式命中，实际: {labels}")

    def test_hit_location_format(self):
        """hits 条目包含 label / text / scene / beat 字段。"""
        from sandbox3.tools.leakcheck import leakcheck
        beat = _make_beat(1, "周默", "编制", "正常", "正常",
                          votes=[_vote(1, "A", "A")], winner_orig_id="A")
        scene = {"index": 1, "beats": [beat]}
        trace = _make_trace([scene])
        result = leakcheck(trace, actor="周默", keywords=["编制"])
        self.assertGreater(len(result["hits"]), 0)
        h = result["hits"][0]
        for key in ("label", "text", "scene", "beat"):
            self.assertIn(key, h, msg=f"hits 条目缺少字段 {key!r}")


# ==================================================================
# __init__ 导出测试
# ==================================================================

class TestToolsInit(unittest.TestCase):
    def test_import_checkup(self):
        from sandbox3.tools import checkup  # noqa: F401

    def test_import_leakcheck(self):
        from sandbox3.tools import leakcheck  # noqa: F401


if __name__ == "__main__":
    unittest.main()
