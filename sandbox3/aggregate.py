# sandbox3/aggregate.py
"""5-run 聚合：同配置不同采样并发跑 N 局，聚合"倾向分布"（论文以 5 run 取均值/众数报数）。
用法：python -m sandbox3.aggregate [--runs 5] [--scenes 4] [--start C1-01] [--seed 42]
产出：output/batch_<时间戳>/run_<i>/(trace.json+台本.md) + aggregate.json + 聚合报告.md
诚实口径（随产物走）：聚合后也只是"该人设在沙盘中的倾向分布"，未经对账校准，不构成预测。
对齐口径：各局 seed 不同、场景序可能分叉——按幕号+行动方软对齐，分叉如实标注（aligned 字段）。"""
from __future__ import annotations
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor

from .engine import run_simulation
from .trace import render
from .states import STATE_ENUMS, STATE_LABELS

FOOTNOTE = ("聚合为该人设在沙盘中的倾向分布；承诺与状态灯未经对账校准，不构成对真实结局的预测；"
            "各局场景序可能分叉，选择按幕号+行动方软对齐，分叉已如实标注。")


def aggregate(traces: list[dict]) -> dict:
    n = len(traces)
    max_scenes = max(len(t["scenes"]) for t in traces)

    # 承诺轨迹：按幕号对齐，均值±极差
    commit = []
    for idx in range(max_scenes):
        vals = [t["scenes"][idx]["commitment"] for t in traces
                if idx < len(t["scenes"]) and t["scenes"][idx]["commitment"] is not None]
        commit.append({"scene": idx + 1, "n": len(vals),
                       "mean": round(sum(vals) / len(vals), 2) if vals else None,
                       "min": min(vals) if vals else None, "max": max(vals) if vals else None})

    # 状态灯终值：众数 + 分布
    lights = {}
    for k in STATE_ENUMS:
        vals = [t["final_state"][k] for t in traces]
        dist = {v: vals.count(v) for v in sorted(set(vals))}
        lights[k] = {"mode": max(dist, key=dist.get), "dist": dist}

    # 表决（拉扯度）/ 黄旗 / 心口缝
    votes = {"全票": 0, "多数票": 0, "摇摆": 0}
    beats = flags = 0
    gap_by_actor: dict[str, int] = {}
    for t in traces:
        for k in votes:
            votes[k] += t["meta"]["vote_stats"].get(k, 0)
        beats += sum(len(s["beats"]) for s in t["scenes"])
        flags += t["meta"]["audit_flags"]
        for actor, c in (t["meta"].get("inner_gaps") or {}).items():
            gap_by_actor[actor] = gap_by_actor.get(actor, 0) + c

    # 每幕选择并排（软对齐：幕号+行动方；场景分叉如实标注）
    choices = []
    for idx in range(max_scenes):
        row = {"scene": idx + 1, "tp_by_run": {}, "aligned": False, "picks": []}
        for ri, t in enumerate(traces, 1):
            if idx >= len(t["scenes"]):
                continue
            sc = t["scenes"][idx]
            row["tp_by_run"][f"run{ri}"] = f"{sc['turning_point']['id']} {sc['turning_point']['title']}"
            for b in sc["beats"]:
                chosen = next((o["text"] for o in b["options_original"]
                               if o["id"] == b["decision"]["chosen_orig_id"]), "")
                row["picks"].append({"run": ri, "beat": b["beat"], "actor": b["acting_agent"],
                                     "chosen": chosen, "vote": b["vote_summary"]["verdict"],
                                     "inner_gap": b["audit"].get("inner_gap") or "无"})
        row["aligned"] = len(set(row["tp_by_run"].values())) == 1
        choices.append(row)

    return {"n_runs": n, "beats_total": beats,
            "commitment_trajectory": commit, "final_lights": lights,
            "vote_stats": votes,
            "sway_rate": round(votes["摇摆"] / beats, 3) if beats else None,
            "audit_flags": flags,
            "audit_flag_rate": round(flags / beats, 3) if beats else None,
            "inner_gaps_total": sum(gap_by_actor.values()),
            "inner_gap_by_actor": gap_by_actor,
            "choices": choices, "footnote": FOOTNOTE}


def render_aggregate(agg: dict, cfg: dict) -> str:
    out = ["# 契合沙盘 · 5-run 聚合报告", "",
           f"- 配置：{agg['n_runs']} 局 × {cfg['scenes']} 幕，起始 {cfg['start']}，"
           f"seed 基值 {cfg['seed']}（逐局 +1）；节骨眼合计 {agg['beats_total']} 个",
           f"- ⚠ {agg['footnote']}", "",
           "## 承诺轨迹（均值 · 区间=极差）", ""]
    out += [f"- 第{c['scene']}幕：{c['mean']}（{c['min']}~{c['max']}，n={c['n']}）"
            for c in agg["commitment_trajectory"]]
    out += ["", "## 状态灯终值（众数 · 分布）", ""]
    for k, v in agg["final_lights"].items():
        dist = " ".join(f"{a}×{b}" for a, b in v["dist"].items())
        out.append(f"- {STATE_LABELS[k]} `{k}`：**{v['mode']}**（{dist}）")
    out += ["", "## 拉扯度（换序三问表决）", "",
            f"- 全票 {agg['vote_stats']['全票']} · 多数票 {agg['vote_stats']['多数票']} · "
            f"摇摆 {agg['vote_stats']['摇摆']}（摇摆率 {agg['sway_rate']:.0%}）——全票=想都不用想，分票=心里打架",
            f"- 审计黄旗 {agg['audit_flags']} 个（黄旗率 {agg['audit_flag_rate']:.0%}）",
            f"- 心口缝（只记录不打分）：共 {agg['inner_gaps_total']} 处"
            f"（{'、'.join(f'{k} {v}' for k, v in agg['inner_gap_by_actor'].items()) or '无'}）",
            "", "## 每幕选择并排（按幕号+行动方软对齐）", ""]
    for row in agg["choices"]:
        tps = set(row["tp_by_run"].values())
        head = f"### 第 {row['scene']} 幕 · " + (
            f"{next(iter(tps))}" if row["aligned"] else f"⚠ 场景分叉：{'；'.join(sorted(tps))}")
        out += [head, ""]
        for p in row["picks"]:
            gap = f"　〔心口缝：{p['inner_gap']}〕" if p["inner_gap"] != "无" else ""
            out.append(f"- run{p['run']} 回合{p['beat']} [{p['actor']}]（{p['vote']}）：{p['chosen']}{gap}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--scenes", type=int, default=4)
    ap.add_argument("--start", default="C1-01")
    ap.add_argument("--seed", type=int, default=42, help="seed 基值，逐局 +1（洗牌可复现）")
    args = ap.parse_args()
    cfg = {"scenes": args.scenes, "start": args.start, "seed": args.seed}

    from .cast import Cast
    from .llm import DeepSeekClient
    from .scenes import SceneBank
    from .config import OUTPUT_DIR

    t0 = time.time()

    def one(i: int) -> dict | None:
        # 单局容错：某局偶发失败（如 LLM 吐坏 JSON 重试后仍败）不连坐整批——
        # 5-run 取均值容许部分缺失；失败明着记 stderr+报告，不静默冒充成功。
        try:
            return run_simulation(cast=Cast.load_default(), llm=DeepSeekClient(),
                                  bank=SceneBank(), n_scenes=args.scenes,
                                  start_tp=args.start, seed=args.seed + i)
        except Exception as e:
            print(f"[aggregate] 第 {i + 1} 局失败，跳过：{type(e).__name__}: {e}", file=sys.stderr)
            return None

    with ThreadPoolExecutor(max_workers=args.runs) as ex:
        raw_traces = list(ex.map(one, range(args.runs)))
    traces = [t for t in raw_traces if t is not None]
    n_ok = len(traces)
    if not traces:
        raise RuntimeError(f"全部 {args.runs} 局失败，无可聚合数据")
    if n_ok < args.runs:
        print(f"[aggregate] {args.runs} 局中 {n_ok} 局成功，{args.runs - n_ok} 局失败，按成功局聚合", file=sys.stderr)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = OUTPUT_DIR / f"batch_{stamp}"
    for i, t in enumerate(traces, 1):
        d = out_dir / f"run_{i}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "trace.json").write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "台本.md").write_text(render(t), encoding="utf-8")
    agg = aggregate(traces)
    agg["batch"] = f"batch_{stamp}"
    agg["config"] = cfg
    agg["elapsed_s"] = round(time.time() - t0, 1)
    (out_dir / "aggregate.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    (out_dir / "聚合报告.md").write_text(render_aggregate(agg, cfg), encoding="utf-8")
    print(f"\n完成：{n_ok}/{args.runs} 局成功，{agg['beats_total']} 节骨眼，{agg['elapsed_s']}s")
    print(f"摇摆率 {agg['sway_rate']:.0%}　黄旗率 {agg['audit_flag_rate']:.0%}　心口缝 {agg['inner_gaps_total']} 处")
    print(f"输出：{out_dir}")


if __name__ == "__main__":
    main()
