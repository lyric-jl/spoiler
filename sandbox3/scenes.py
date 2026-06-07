# sandbox3/scenes.py
"""场景库：12 条预设（data/scene_bank.json，蓝本逐字迁移）+ 自定义持久化。
去重从简：同名加后缀（作者拍，不上相似度算法）。"""
from __future__ import annotations
import json
import pathlib

from .config import DATA_DIR

CATEGORIES = ("初来乍到", "磨合建制", "压力测试", "冲突与修复", "深化里程碑", "现代职场")
_PRESET_PATH = DATA_DIR / "scene_bank.json"


class SceneBank:
    def __init__(self, custom_path: pathlib.Path | None = None):
        self.custom_path = custom_path or (DATA_DIR / "custom_scenes.json")
        self._presets = json.loads(_PRESET_PATH.read_text(encoding="utf-8"))
        self._custom: list[dict] = []
        if self.custom_path.exists():
            self._custom = json.loads(self.custom_path.read_text(encoding="utf-8"))

    def all(self) -> list[dict]:
        return self._presets + self._custom

    def by_id(self, sid: str) -> dict:
        for t in self.all():
            if t["id"] == sid:
                return t
        raise KeyError(f"场景 {sid!r} 不存在")

    def candidates(self, categories: list[str], used: set[str]) -> list[dict]:
        return [t for t in self.all() if t["category"] in categories and t["id"] not in used] \
            or [t for t in self.all() if t["id"] not in used]

    def add_custom(self, raw: dict) -> dict:
        title = str(raw.get("title") or "自定义场景")
        existing = {t["title"] for t in self.all()}
        n, t2 = 2, title
        while t2 in existing:
            t2 = f"{title}·{n}"
            n += 1
        nums = [int(t["id"][2:]) for t in self._custom
                if str(t.get("id", "")).startswith("X-") and str(t["id"])[2:].isdigit()]
        new_id = f"X-{(max(nums) if nums else 0) + 1:02d}"
        scene = {"id": new_id, "title": t2,
                 "category": raw.get("category") if raw.get("category") in CATEGORIES else "现代职场",
                 "sketch": str(raw.get("sketch") or ""),
                 "owner_hints": str(raw.get("owner_hints") or "")}
        self._custom.append(scene)
        self.custom_path.parent.mkdir(parents=True, exist_ok=True)
        self.custom_path.write_text(json.dumps(self._custom, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
        return scene
