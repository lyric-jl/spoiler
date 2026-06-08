# tests/test_data_integrity.py
"""数据文件完整性哨兵：防多源人设漂移。"""
import json
import pathlib
import unittest

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


class TestCastDataIntegrity(unittest.TestCase):
    def test_cast_three_first_two_match_default(self):
        """cast_three.json 前两卡（周默/沈雯）必须与 cast_default.json 逐字段一致。
        改了 default 忘改 three 会在此报红——别让同一人物在 2 人局/3 人局人设漂移。"""
        default = json.loads((DATA / "cast_default.json").read_text(encoding="utf-8"))
        three = json.loads((DATA / "cast_three.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(three), len(default))
        for d, t in zip(default, three):
            self.assertEqual(d, t, f"漂移：{d.get('name')} 在 cast_default 与 cast_three 不一致")

    def test_cast_three_has_three_distinct_kinds(self):
        """cast_three = candidate + counterpart + colleague 三类齐。"""
        three = json.loads((DATA / "cast_three.json").read_text(encoding="utf-8"))
        kinds = [c["kind"] for c in three]
        self.assertEqual(len(three), 3)
        self.assertEqual(set(kinds), {"candidate", "counterpart", "colleague"})


if __name__ == "__main__":
    unittest.main()
