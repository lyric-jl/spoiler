# tests/test_scenes.py
import tempfile, pathlib, unittest

from sandbox3 import scenes as S


class TestSceneBank(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.bank = S.SceneBank(custom_path=self.tmp / "custom.json")

    def test_presets_loaded(self):
        all_scenes = self.bank.all()
        self.assertGreaterEqual(len(all_scenes), 12)                          # 至少 12 条预设（扩充后更多）
        self.assertEqual(len({t["id"] for t in all_scenes}), len(all_scenes))  # id 全唯一

    def test_by_id(self):
        self.assertEqual(self.bank.by_id("C1-01")["category"], "初来乍到")

    def test_add_custom_persists(self):
        sc = self.bank.add_custom({"title": "新场景", "category": "现代职场",
                                   "sketch": "素描", "owner_hints": "提示"})
        self.assertTrue(sc["id"].startswith("X-"))
        bank2 = S.SceneBank(custom_path=self.tmp / "custom.json")
        self.assertIn(sc["id"], {t["id"] for t in bank2.all()})

    def test_duplicate_title_suffixed(self):
        self.bank.add_custom({"title": "撞名", "category": "现代职场", "sketch": "a", "owner_hints": ""})
        sc2 = self.bank.add_custom({"title": "撞名", "category": "现代职场", "sketch": "b", "owner_hints": ""})
        self.assertNotEqual(sc2["title"], "撞名")

    def test_bad_category_falls_back(self):
        sc = self.bank.add_custom({"title": "x", "category": "不存在", "sketch": "s", "owner_hints": ""})
        self.assertEqual(sc["category"], "现代职场")

    def test_candidates_excludes_used(self):
        cands = self.bank.candidates(["初来乍到"], used={"C1-01"})
        self.assertNotIn("C1-01", {c["id"] for c in cands})

    def test_id_no_reuse_after_delete(self):
        sc1 = self.bank.add_custom({"title": "场景A", "category": "现代职场", "sketch": "a", "owner_hints": ""})
        sc2 = self.bank.add_custom({"title": "场景B", "category": "现代职场", "sketch": "b", "owner_hints": ""})
        sc3 = self.bank.add_custom({"title": "场景C", "category": "现代职场", "sketch": "c", "owner_hints": ""})
        # 模拟删档：手动从 _custom 删掉中间一条并重写持久化
        self.bank._custom = [t for t in self.bank._custom if t["id"] != sc2["id"]]
        self.bank.custom_path.write_text(
            __import__("json").dumps(self.bank._custom, ensure_ascii=False, indent=2),
            encoding="utf-8")
        sc4 = self.bank.add_custom({"title": "场景D", "category": "现代职场", "sketch": "d", "owner_hints": ""})
        existing_ids = {t["id"] for t in self.bank._custom if t["id"] != sc4["id"]}
        self.assertNotIn(sc4["id"], existing_ids)
        # 新 id 必须大于现存最大序号（sc3 是 X-03，新的应为 X-04）
        self.assertGreater(int(sc4["id"][2:]), int(sc3["id"][2:]))


if __name__ == "__main__":
    unittest.main()
