# evidence/p3/_smoke_p3.py
"""P3 新场景逐条 live 冒烟（LIVE，花真钱）。
等价 CLI：python -m sandbox3.run --scenes 1 --start <id> --seed 42（逐条）
验证 3 条新场景各能作为起始场景全链跑通、0 未处理异常。"""
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

EV = pathlib.Path("evidence/p3")
EV.mkdir(parents=True, exist_ok=True)
LLM = DeepSeekClient()
log, results = [], []


def p(m):
    print(m, flush=True)
    log.append(m)


NEW = ["C3-03", "C4-03", "C6-03"]
try:
    bank = SceneBank()
    for sid in NEW:
        title = bank.by_id(sid)["title"]
        p(f"\n=== 冒烟 {sid}「{title}」 ===")
        t0 = time.time()
        tr = run_simulation(cast=Cast.load_default(), llm=LLM, bank=bank,
                            n_scenes=1, start_tp=sid, seed=42)
        tr["meta"]["elapsed_s"] = round(time.time() - t0, 1)
        d = save_run(tr)
        m = tr["meta"]
        sc = tr["scenes"][0]
        n_beats = len(sc.get("beats", []))
        ok = n_beats >= 1 and m.get("warnings_total", 0) is not None
        p(f"  -> {d.name} calls={m.get('n_llm_calls')} warns={m.get('warnings_total')} "
          f"beats={n_beats} {m['elapsed_s']}s  冒烟={'PASS' if ok else 'FAIL'}")
        p(f"  场景开场：{sc.get('current_scene','')[:90]}")
        results.append({"id": sid, "title": title, "run_dir": d.name,
                        "calls": m.get("n_llm_calls"), "warns": m.get("warnings_total"),
                        "beats": n_beats, "ok": ok})
    allok = all(r["ok"] for r in results)
    p(f"\n=== P3 冒烟汇总：{sum(r['ok'] for r in results)}/{len(results)} PASS（全过={allok}）===")
    (EV / "p3_smoke.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
except Exception as e:
    import traceback
    p(f"[ERROR] {type(e).__name__}: {e}")
    p(traceback.format_exc())
finally:
    (EV / "smoke_log.txt").write_text("\n".join(log), encoding="utf-8")
