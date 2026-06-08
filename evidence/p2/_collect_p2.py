# evidence/p2/_collect_p2.py
"""P2 蒸馏闭环验收 · 客观证据采集（LIVE，花真钱）。
等价 CLI：
  python -m sandbox3.distill data/materials_zhou --out evidence/p2/card_zhou_distilled.json
  （拼蒸馏卡+沈雯卡）→ python -m sandbox3.run --scenes 2 --cast <拼合> --seed 42
客观提取：蒸馏产卡过校验 / 那条埋的视角分歧（自评冷静 vs 面试官应激）有没有两面进人设 / 拼名单跑局成功。"""
from __future__ import annotations
import sys, io, os, json, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from sandbox3.cast import Cast
from sandbox3.distill import distill
from sandbox3.engine import run_simulation
from sandbox3.llm import DeepSeekClient
from sandbox3.scenes import SceneBank
from sandbox3.trace import save_run

EV = pathlib.Path("evidence/p2")
EV.mkdir(parents=True, exist_ok=True)
log = []


def p(m):
    print(m, flush=True)
    log.append(m)


try:
    LLM = DeepSeekClient()
    # 1) 真蒸馏周默卡
    p("=== 蒸馏：data/materials_zhou → 周默卡 ===")
    t0 = time.time()
    card = distill(LLM, pathlib.Path("data/materials_zhou"))
    p(f"[蒸馏完成] {round(time.time()-t0,1)}s　name={card.get('name')} kind={card.get('kind')}")
    (EV / "card_zhou_distilled.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    persona = card.get("persona", "")
    playbook = card.get("playbook", [])
    full = persona + " " + " ".join(playbook)
    p(f"\n[persona]\n{persona}\n")
    p("[playbook]")
    for i, pb in enumerate(playbook, 1):
        p(f"  {i}. {pb}")

    # 2) 客观检测：那条埋的视角分歧（自评冷静 vs 面试官应激）有没有两面进人设
    self_side = [w for w in ("冷静", "抗压", "不慌", "稳", "镇定", "沉着") if w in full]
    other_side = [w for w in ("语速", "加快", "应激", "紧张", "敲", "急促", "面试官", "观察", "看得出") if w in full]
    p(f"\n[视角分歧检测]")
    p(f"  自评侧词命中（冷静/抗压…）: {self_side}")
    p(f"  他人观察侧词命中（语速/应激/面试官…）: {other_side}")
    both = bool(self_side) and bool(other_side)
    p(f"  → 两面是否并存于人设: {both}（True=保留视角分歧不调和纪律 live 成立）")

    # 3) 拼名单（蒸馏周默卡 + 沈雯 counterpart）跑 2 幕局
    default_cards = json.loads(pathlib.Path("data/cast_default.json").read_text(encoding="utf-8"))
    shen = [c for c in default_cards if c.get("kind") == "counterpart"][0]
    merged = [card, shen]
    (EV / "cast_distilled_merged.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    cast = Cast.from_cards(merged)
    p(f"\n=== 拼名单跑局：{cast.names()} ===")
    t1 = time.time()
    tr = run_simulation(cast=cast, llm=LLM, bank=SceneBank(), n_scenes=2, start_tp="C1-01", seed=42)
    tr["meta"]["elapsed_s"] = round(time.time() - t1, 1)
    d = save_run(tr)
    m = tr["meta"]
    p(f"[跑局完成] -> {d} calls={m.get('n_llm_calls')} warns={m.get('warnings_total')} {m['elapsed_s']}s")
    p(f"[行动方分布] {m.get('actor_counts')}")

    # 提取周默几个决策行为供人判"行为顺材料证据"
    behaviors = []
    for si, sc in enumerate(tr["scenes"], 1):
        for b in sc.get("beats", []):
            if b.get("acting_agent") == "周默":
                act = (b.get("decision") or {}).get("action", "")
                inner = (b.get("appraisal") or {}).get("internal_thoughts", "")
                behaviors.append({"scene": si, "beat": b.get("beat"),
                                  "action": act[:80], "inner": inner[:80]})
    for bh in behaviors:
        p(f"  幕{bh['scene']}·回合{bh['beat']} 行动={bh['action']}")

    summary = {
        "distilled_card": {"name": card.get("name"), "role": card.get("role"),
                           "persona_len": len(persona), "playbook_n": len(playbook)},
        "perspective_tension": {"self_side": self_side, "other_side": other_side, "both_present": both},
        "run_dir": d.name, "calls": m.get("n_llm_calls"), "warns": m.get("warnings_total"),
        "actor_counts": m.get("actor_counts"), "zhou_behaviors": behaviors,
    }
    (EV / "p2_evidence.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    p("\n=== P2 蒸馏闭环客观证据采集完成 ===")
except Exception as e:
    import traceback
    p(f"[ERROR] {type(e).__name__}: {e}")
    p(traceback.format_exc())
finally:
    (EV / "collect_log.txt").write_text("\n".join(log), encoding="utf-8")
