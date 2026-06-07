# sandbox3/engine.py
"""推演循环（名单制多人原生底座；蓝本=relate_mvp engine.py，机制行为等价迁移）。
机制清单：受控选项决策 / 换序三问取多数票 / 差量状态灯 / 防火墙（知情过滤）/
理由审计（独立调用）/ 台账时间线 / 后果结算 / ≥3灯黄旗。
依赖注入：run_simulation(cast=名单, llm=客户端, bank=场景库)——测试喂 FakeLLM，运行时唯一路径=DeepSeek live。"""
from __future__ import annotations
import random
import sys

from . import audit as AU
from .cast import Cast
from .config import MAX_BEATS, VOTE_ROUNDS
from .ledger import entry, ledger_text, visible
from .prompts import agent as PA
from .prompts import sm as PS
from .states import initial_state, apply_state_deltas, plausible_categories


def _log(msg: str) -> None:
    print(msg, flush=True)


def _coerce_options(raw) -> list[dict]:
    opts = []
    if isinstance(raw, list):
        for i, o in enumerate(raw):
            if isinstance(o, dict) and o.get("text"):
                opts.append({"id": str(o.get("id") or "ABCD"[i % 4]), "text": str(o["text"])})
    return opts


def _build_presentations(options: list[dict], rng: random.Random) -> list[list[dict]]:
    """洗牌一次得第1问呈现序，再逐问轮转——三问顺序互不相同、每个选项换坑位。
    每问按呈现位次重发 A/B/C/D，保留 orig_id 供对账。"""
    base = options[:]
    rng.shuffle(base)
    rounds = []
    for r in range(VOTE_ROUNDS):
        k = r % len(base)
        rot = base[k:] + base[:k]
        rounds.append([{"id": "ABCD"[i], "text": o["text"], "orig_id": o["id"]}
                       for i, o in enumerate(rot)])
    return rounds


def _tally_votes(votes: list[dict]) -> dict:
    """按内容（orig_id）计票：全票/多数票/摇摆（摇摆取第1问，入档是信号不是噪声）。"""
    tally: dict[str, int] = {}
    for v in votes:
        tally[v["orig_id"]] = tally.get(v["orig_id"], 0) + 1
    top = max(tally.values())
    verdict = "全票" if top == len(votes) else ("多数票" if top >= 2 else "摇摆")
    winner = next(v for v in votes if tally[v["orig_id"]] == top)
    return {"rounds": len(votes), "tally": tally, "verdict": verdict,
            "winner_orig_id": winner["orig_id"], "winner_round": winner["round"]}
