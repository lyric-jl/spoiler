# evidence/p0/_collect_live.py
"""P0 验收闸门 · 客观证据采集（LIVE，花真钱）。
等价 CLI：
  python -m sandbox3.run --scenes 4 --seed 42
  python -m sandbox3.run --scenes 4 --seed 7
  python -m sandbox3.tools.checkup output/run_<42> output/run_<7>
  python -m sandbox3.run --scenes 2 --start C5-02 --seed 7
  python -m sandbox3.tools.leakcheck output/run_<leak> 周默 编制,合并,缩编,裁员,HC
本脚本直接调同名函数，串行跑，把结论写 evidence/p0/。"""
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
from sandbox3.tools.checkup import checkup
from sandbox3.tools.leakcheck import leakcheck

EV = pathlib.Path("evidence/p0")
EV.mkdir(parents=True, exist_ok=True)
LLM = DeepSeekClient()
log_lines = []


def log(msg):
    print(msg, flush=True)
    log_lines.append(msg)


def one(scenes, seed, start="C1-01"):
    t0 = time.time()
    tr = run_simulation(cast=Cast.load_default(), llm=LLM, bank=SceneBank(),
                        n_scenes=scenes, start_tp=start, seed=seed)
    tr["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    d = save_run(tr)
    m = tr["meta"]
    log(f"[done] scenes={scenes} seed={seed} start={start} -> {d} "
        f"calls={m.get('n_llm_calls')} warns={m.get('warnings_total')} {m['elapsed_s']}s")
    return tr, d


try:
    log("=== P0 证据采集开始 ===")
    # 1) checkup pair：scenes=4 两局换序三问防位置偏置
    tr42, d42 = one(4, 42)
    tr7, d7 = one(4, 7)
    ck = checkup([d42, d7])
    (EV / "checkup.json").write_text(json.dumps(ck, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[checkup] verdict={ck.get('verdict')} A占比={ck.get('winner_pos_a_ratio')} "
        f"winner_pos={ck.get('winner_pos_counts')} total_beats={ck.get('total_beats')}")

    # 2) leakcheck：scenes=2 start C5-02（缩编敏感场景）防火墙泄漏
    tr_leak, d_leak = one(2, 7, start="C5-02")
    lk = leakcheck(tr_leak, "周默", ["编制", "合并", "缩编", "裁员", "HC"])
    (EV / "leakcheck.json").write_text(json.dumps(lk, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"[leakcheck] hit_count={lk.get('hit_count')} ok_mentions={len(lk.get('ok_mentions', []))}")

    log("=== 全部 live 局完成 ===")
    log(f"checkup run dirs: {d42.name}, {d7.name}")
    log(f"leakcheck run dir: {d_leak.name}")
except Exception as e:
    import traceback
    log(f"[ERROR] {type(e).__name__}: {e}")
    log(traceback.format_exc())
finally:
    (EV / "collect_log.txt").write_text("\n".join(log_lines), encoding="utf-8")
