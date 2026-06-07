# sandbox3/tools/checkup.py
"""位置偏置体检工具（转正版）。

原型：_checkup.py（蓝本临时脚本，因文件不存在已从 engine.py 末尾的 pos_counts 逻辑重建）。

checkup(run_dirs) 聚合多个 run 目录中 trace.json 的 votes 数据，统计：
- position_counts: 每个呈现位（A/B/C/D）被各问选中的总次数
- winner_pos_a_ratio: 官方选择（winner_orig_id）在第1问呈现位为 A 的比例
- total_beats / total_votes: 汇总计数
- verdict: "pass（位置偏置在合理范围）" 或 "fail（位置偏置，A 位占比偏离 1/3）"

判读口径：winner 第1问呈现位 A 占比在 [1/4, 2/5] 以内视为过（约1/3上下浮动25%）。

__main__：接收 run 目录路径列表，打印结果。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 判通过的 A 位占比区间（约 1/3 上下 ±约 25% 相对）
_PASS_LO = 0.20
_PASS_HI = 0.47


def checkup(run_dirs: list[Path]) -> dict:
    """对一组 run 目录做位置偏置体检。

    Args:
        run_dirs: 含 trace.json 的目录路径列表。

    Returns:
        dict，含以下键：
        - run_count (int): 处理的 run 目录数
        - total_beats (int): 有效回合总数
        - total_votes (int): 投票总条数（beats × vote_rounds）
        - position_counts (dict[str, int]): 各呈现位被选中次数
        - winner_pos_counts (dict[str, int]): 官方选择第1问呈现位分布
        - winner_pos_a_ratio (float): 官方选择第1问呈现位为 A 的比例
        - verdict (str): "pass（...）" 或 "fail（...）"
    """
    position_counts: dict[str, int] = {}
    winner_pos_counts: dict[str, int] = {}
    total_beats = 0
    total_votes = 0
    run_count = 0

    for d in run_dirs:
        d = Path(d)
        trace_file = d / "trace.json"
        if not trace_file.exists():
            continue
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        run_count += 1

        for sc in trace.get("scenes", []):
            for bt in sc.get("beats", []):
                votes = bt.get("votes") or []
                if not votes:
                    continue
                total_beats += 1
                for v in votes:
                    pos = v.get("position", "?")
                    position_counts[pos] = position_counts.get(pos, 0) + 1
                    total_votes += 1

                # winner_orig_id 对应的第1问（round==1）呈现位
                winner_orig = bt.get("vote_summary", {}).get("winner_orig_id", "")
                round1_vote = next(
                    (v for v in votes if v.get("round") == 1), None)
                if round1_vote and winner_orig:
                    # 找第1问里 winner_orig_id 对应的呈现位
                    # round1 vote 的 orig_id 就是该问实际选择——但我们要找 winner 在第1问的位置
                    # votes 记录的是"该问选择了哪个"，winner 是多数票胜出的 orig_id
                    # 需要在第1问的 order 里找 winner 的坑位
                    order = round1_vote.get("order") or []
                    # order 是 [orig_id, ...] 按 A/B/C/D 顺序
                    if winner_orig in order:
                        idx = order.index(winner_orig)
                        winner_pos = "ABCD"[idx] if idx < 4 else "?"
                    else:
                        # order 信息不全时降级：取第1问的 position 字段（若与 orig 一致则直接用）
                        winner_pos = round1_vote.get("position", "?") \
                            if round1_vote.get("orig_id") == winner_orig else "?"
                    winner_pos_counts[winner_pos] = winner_pos_counts.get(winner_pos, 0) + 1

    winner_a = winner_pos_counts.get("A", 0)
    total_winners = sum(winner_pos_counts.values())
    winner_pos_a_ratio = winner_a / total_winners if total_winners > 0 else 0.0

    if total_winners == 0:
        verdict = "skip（无有效回合，无法判定）"
    elif _PASS_LO <= winner_pos_a_ratio <= _PASS_HI:
        verdict = (f"pass（位置偏置在合理范围；A位占比 {winner_pos_a_ratio:.1%}，"
                   f"期望区间 [{_PASS_LO:.0%}, {_PASS_HI:.0%}]）")
    else:
        verdict = (f"fail（位置偏置；A位占比 {winner_pos_a_ratio:.1%}，"
                   f"偏离期望区间 [{_PASS_LO:.0%}, {_PASS_HI:.0%}]）")

    return {
        "run_count": run_count,
        "total_beats": total_beats,
        "total_votes": total_votes,
        "position_counts": position_counts,
        "winner_pos_counts": winner_pos_counts,
        "winner_pos_a_ratio": winner_pos_a_ratio,
        "verdict": verdict,
    }


def _print_result(result: dict) -> None:
    print(f"run 目录数：{result['run_count']}")
    print(f"有效回合数：{result['total_beats']}，投票总条数：{result['total_votes']}")
    print(f"\n呈现位被选分布（所有问次）：")
    for pos in sorted(result["position_counts"]):
        print(f"  {pos}: {result['position_counts'][pos]}")
    print(f"\n官方选择第1问呈现位分布：")
    for pos in sorted(result["winner_pos_counts"]):
        print(f"  {pos}: {result['winner_pos_counts'][pos]}")
    print(f"\nwinner 第1问 A 位占比：{result['winner_pos_a_ratio']:.1%}")
    print(f"判定：{result['verdict']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python -m sandbox3.tools.checkup <run_dir> [run_dir ...]")
        sys.exit(1)
    dirs = [Path(p) for p in sys.argv[1:]]
    _print_result(checkup(dirs))
