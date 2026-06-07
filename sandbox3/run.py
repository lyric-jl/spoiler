# sandbox3/run.py
"""入口：python -m sandbox3.run [--scenes 4] [--start C1-01] [--seed S] [--cast path.json]"""
from __future__ import annotations
import argparse, json, pathlib, time

from .cast import Cast
from .engine import run_simulation
from .llm import DeepSeekClient
from .scenes import SceneBank
from .trace import save_run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, default=4)
    ap.add_argument("--start", default="C1-01")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--cast", default=None, help="名单 JSON 路径（缺省用 data/cast_default.json）")
    args = ap.parse_args()
    cast = Cast.from_cards(json.loads(pathlib.Path(args.cast).read_text(encoding="utf-8"))) \
        if args.cast else Cast.load_default()
    t0 = time.time()
    trace = run_simulation(cast=cast, llm=DeepSeekClient(), bank=SceneBank(),
                           n_scenes=args.scenes, start_tp=args.start, seed=args.seed)
    trace["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = save_run(trace)
    print(f"\n完成：{trace['meta']['n_scenes']} 幕，{trace['meta']['n_llm_calls']} 次调用，"
          f"{trace['meta']['elapsed_s']}s，警告 {trace['meta']['warnings_total']} 条\n输出：{out}")


if __name__ == "__main__":
    main()
