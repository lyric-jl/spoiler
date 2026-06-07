# tests/test_scenes.py
import tempfile, pathlib, unittest

from sandbox3 import scenes as S


class TestSceneBank(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.bank = S.SceneBank(custom_path=self.tmp / "custom.json")

    def test_presets_loaded(self):
        self.assertEqual(len(self.bank.all()), 12)
        self.assertEqual(len({t["id"] for t in self.bank.all()}), 12)

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


if __name__ == "__main__":
    unittest.main()
