# evidence/p1/_collect_p1.py
"""P1 三人局验收 · 客观证据采集（LIVE，花真钱）。
等价 CLI：python -m sandbox3.run --scenes 3 --seed 42 --cast data/cast_three.json
客观提取：行动方分布（陈磊是否有真决策回合）/ 陈磊 beat 管线齐 / 每幕 relations 两行细目。"""
from __future__ import annotations
import sys, io, os, json, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from sandbox3.cast import Cast
from sandbox3.engine import run_simulation
from sandbox3.llm import DeepSeekClient
from sandbox3.scenes import SceneBank
from sandbox3.trace import save_run

EV = pathlib.Path("evidence/p1")
EV.mkdir(parents=True, exist_ok=True)
log = []


def p(m):
    print(m, flush=True)
    log.append(m)


try:
    cast = Cast.from_cards(json.loads(pathlib.Path("data/cast_three.json").read_text(encoding="utf-8")))
    p(f"[cast] {cast.names()} candidate={cast.candidate().name}")
    t0 = time.time()
    tr = run_simulation(cast=cast, llm=DeepSeekClient(), bank=SceneBank(),
                        n_scenes=3, start_tp="C1-01", seed=42)
    tr["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    d = save_run(tr)
    m = tr["meta"]
    p(f"[done] -> {d} calls={m.get('n_llm_calls')} warns={m.get('warnings_total')} {m['elapsed_s']}s")

    # 客观证据①：行动方分布
    ac = m.get("actor_counts", {})
    p(f"[行动方分布] {ac}")
    chen = "陈磊"
    p(f"[陈磊作为行动方次数] {ac.get(chen, 0)}（>0 即非布景、有真决策回合）")

    # 客观证据②：陈磊 beat 管线齐（appraisal/votes/audit）
    chen_beats = []
    for si, sc in enumerate(tr["scenes"], 1):
        for b in sc.get("beats", []):
            if b.get("acting_agent") == chen:
                has = {k: (k in b and bool(b[k])) for k in ("appraisal", "votes", "audit")}
                chen_beats.append({"scene": si, "beat": b.get("beat"), "pipeline": has,
                                   "chosen": (b.get("decision") or {}).get("action", "")[:60]})
    p(f"[陈磊完整管线 beat 数] {len(chen_beats)}")
    for cb in chen_beats:
        p(f"   幕{cb['scene']}·回合{cb['beat']} 管线齐={all(cb['pipeline'].values())} {cb['pipeline']} 选择={cb['chosen']}")

    # 客观证据③：每幕 relations 两行细目（候选人×沈雯/陈磊）
    rel_report = []
    for si, sc in enumerate(tr["scenes"], 1):
        rel = sc.get("relations", {})
        rel_report.append({"scene": si, "members": sorted(rel.keys()),
                           "detail": {k: (v.get("attitude"), (v.get("evidence") or "")[:40]) for k, v in rel.items()}})
        p(f"[幕{si} relations] {sorted(rel.keys())} -> {rel_report[-1]['detail']}")

    summary = {
        "run_dir": d.name, "calls": m.get("n_llm_calls"), "warns": m.get("warnings_total"),
        "actor_counts": ac, "chen_acting_count": ac.get(chen, 0),
        "chen_full_pipeline_beats": chen_beats, "relations_per_scene": rel_report,
    }
    (EV / "p1_evidence.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    p("=== P1 客观证据采集完成 ===")
except Exception as e:
    import traceback
    p(f"[ERROR] {type(e).__name__}: {e}")
    p(traceback.format_exc())
finally:
    (EV / "collect_log.txt").write_text("\n".join(log), encoding="utf-8")
