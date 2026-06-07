# sandbox3/cast.py
"""名单制角色注册表（多人原生底座：双人=N=2 特例）。
设计要点：引擎显式接收 Cast 对象（无模块全局变量）；candidate（观察主体）有且仅有一个。"""
from __future__ import annotations
import json
import pathlib
from dataclasses import dataclass

from .config import DATA_DIR, MAX_CAST

KINDS = ("candidate", "counterpart", "colleague")


class CastError(ValueError):
    pass


@dataclass(frozen=True)
class Card:
    name: str
    kind: str
    role: str
    persona: str
    playbook: tuple[str, ...]


class Cast:
    def __init__(self, cards: list[Card]):
        self._cards = cards

    # ---- 构造与校验 ----
    @classmethod
    def from_cards(cls, raw_cards: list[dict]) -> "Cast":
        if not 2 <= len(raw_cards) <= MAX_CAST:
            raise CastError(f"名单需 2-{MAX_CAST} 人，得到 {len(raw_cards)}")
        cards, names = [], set()
        for rc in raw_cards:
            for k in ("name", "kind", "role", "persona", "playbook"):
                if not rc.get(k):
                    raise CastError(f"角色卡缺字段 {k}：{rc.get('name', '?')}")
            if rc["kind"] not in KINDS:
                raise CastError(f"kind 越界（{rc['kind']!r}），须为 {KINDS}")
            if not isinstance(rc["playbook"], list) or not 3 <= len(rc["playbook"]) <= 9:
                raise CastError(f"{rc['name']} 的 playbook 需为 3-9 条列表")
            if rc["name"] in names:
                raise CastError(f"人名重复：{rc['name']}")
            names.add(rc["name"])
            cards.append(Card(str(rc["name"]), rc["kind"], str(rc["role"]),
                              str(rc["persona"]), tuple(str(r) for r in rc["playbook"])))
        cands = [c for c in cards if c.kind == "candidate"]
        if len(cands) != 1:
            raise CastError(f"candidate（观察主体）须有且仅有 1 个，得到 {len(cands)}")
        return cls(cards)

    @classmethod
    def load_default(cls) -> "Cast":
        p = DATA_DIR / "cast_default.json"
        return cls.from_cards(json.loads(p.read_text(encoding="utf-8")))

    # ---- 查询 ----
    def members(self) -> list[Card]:
        return list(self._cards)

    def candidate(self) -> Card:
        return next(c for c in self._cards if c.kind == "candidate")

    def others(self) -> list[Card]:
        return [c for c in self._cards if c.kind != "candidate"]

    def names(self) -> list[str]:
        return [c.name for c in self._cards]

    def get(self, name: str) -> Card:
        try:
            return next(c for c in self._cards if c.name == name)
        except StopIteration:
            raise CastError(f"名单上没有 {name!r}") from None

    def persona_block(self, name: str) -> str:
        c = self.get(name)
        rules = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(c.playbook))
        return f"【身份】{c.role}\n【人设】{c.persona}\n【行为手册（如果…就…）】\n{rules}"
