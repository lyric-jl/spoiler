# sandbox3/tools/leakcheck.py
"""防火墙泄漏检查工具（转正版）。

原型：_leakcheck.py（蓝本临时脚本，路径
  D:/aidasai/fitsandbox/relate_mvp/output/_leakcheck.py）已读入并等价迁移。

主要变更（函数化+参数化）：
1. actor 和 keywords 改为参数（原脚本硬编码"周默"和 KEYWORDS 正则）。
2. leakcheck(trace, actor, keywords) 返回结构化 dict，不直接 print。
3. 叙事认知句式正则由硬编码"周默"改为 f-string 插入 actor 参数。
4. 增加 options（给该 actor 的选项文本）扫描（原脚本有此项）。
5. __main__ 接 run 目录 + actor + 逗号分隔关键词，与蓝本等价。

关键词为子串匹配——高召回、可能误报（如"编制"命中"编制预算"），结果供人工复核，不作自动判定。

判读语义不变：
- 目标 actor 的内心/选择理由/行动/各问投票理由/给他的选项/叙事认知句式 → hits
- 其他角色内心含关键词 → ok_mentions（知情者合法，不计泄漏）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def leakcheck(trace: dict, actor: str, keywords: list[str]) -> dict:
    """扫描 trace 中 actor 侧文本是否泄漏了不该知道的关键词。

    Args:
        trace: run_simulation 产出的 trace dict（含 scenes/beats 结构）。
        actor: 被检查泄漏的目标角色名（例如"周默"）。
        keywords: 禁止出现在该 actor 侧的关键词列表（例如 ["编制", "合并"]）。

    Returns:
        dict，含：
        - hit_count (int): 命中次数
        - hits (list[dict]): 每条命中，含 label/text/scene/beat
        - ok_mentions (list[str]): 其他角色内心的合法关键词提及（不计泄漏）
        - conclusion (str): 结论文字
    """
    if not keywords:
        return {"hit_count": 0, "hits": [], "ok_mentions": [],
                "conclusion": "关键词列表为空，跳过检查"}

    kw_pattern = re.compile("|".join(re.escape(k) for k in keywords))
    # 叙事认知句式："{actor}[^。]{0,30}(脑子|心想|心里|念头|想起|闪过)"
    narr_pattern = re.compile(
        rf"{re.escape(actor)}[^。]{{0,30}}(脑子|心想|心里|念头|想起|闪过)[^。]*。"
    )

    hits: list[dict] = []
    ok_mentions: list[str] = []

    for sc in trace.get("scenes", []):
        sc_idx = sc.get("index", "?")
        for bt in sc.get("beats", []):
            bt_no = bt.get("beat", "?")
            acting = bt.get("acting_agent", "")

            # ── 叙事认知句式（公共文本，但 actor 视角句=泄漏）──
            narr = bt.get("narration", "")
            for m in re.finditer(narr_pattern, narr):
                if kw_pattern.search(m.group(0)):
                    hits.append({
                        "label": f"叙事中{actor}认知",
                        "text": m.group(0)[:120],
                        "scene": sc_idx,
                        "beat": bt_no,
                    })

            if acting == actor:
                # ── actor 侧文本扫描 ──
                spots: list[tuple[str, str]] = []

                # 内心
                spots.append((
                    f"{actor}内心",
                    bt.get("appraisal", {}).get("internal_thoughts", "")
                ))
                # 选择理由
                spots.append((
                    f"{actor}选择理由",
                    bt.get("decision", {}).get("reasoning", "")
                ))
                # 行动
                spots.append((
                    f"{actor}行动",
                    bt.get("decision", {}).get("action", "")
                ))
                # 换序三问各投票理由
                for v in bt.get("votes") or []:
                    spots.append((
                        f"{actor}第{v.get('round', '?')}问理由",
                        v.get("reasoning", "")
                    ))
                # 给该 actor 的选项文本
                for o in bt.get("options") or []:
                    spots.append((
                        f"给{actor}的选项{o.get('id', '?')}",
                        o.get("text", "")
                    ))

                for label, txt in spots:
                    if txt and kw_pattern.search(txt):
                        hits.append({
                            "label": label,
                            "text": txt[:120],
                            "scene": sc_idx,
                            "beat": bt_no,
                        })

            else:
                # ── 其他角色内心（知情者合法提及）──
                other_thoughts = bt.get("appraisal", {}).get("internal_thoughts", "")
                if other_thoughts and kw_pattern.search(other_thoughts):
                    ok_mentions.append(
                        f"第{sc_idx}幕回合{bt_no} {acting}内心提及（合法，该角色知情）"
                    )

    hit_count = len(hits)
    if hit_count == 0:
        conclusion = f"{actor}侧无关键词泄漏（防火墙完好）"
    else:
        conclusion = f"防火墙击穿：{actor}侧发现 {hit_count} 处关键词泄漏"

    return {
        "hit_count": hit_count,
        "hits": hits,
        "ok_mentions": ok_mentions,
        "conclusion": conclusion,
    }


def _print_result(run_dir: Path, actor: str, result: dict) -> None:
    print(f"检查 run: {run_dir.name}")
    print(f"目标 actor: {actor}")
    print(f"泄漏命中: {result['hit_count']}")
    for h in result["hits"]:
        print(f"  ✗ 第{h['scene']}幕回合{h['beat']}【{h['label']}】{h['text']}")
    for m in result["ok_mentions"]:
        print(f"  ○ {m}")
    print(f"结论：{result['conclusion']}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法：python -m sandbox3.tools.leakcheck <run_dir> <actor> <关键词1,关键词2,...>")
        sys.exit(1)
    run_dir = Path(sys.argv[1])
    actor = sys.argv[2]
    keywords = [k.strip() for k in sys.argv[3].split(",") if k.strip()]
    trace_file = run_dir / "trace.json"
    if not trace_file.exists():
        sys.exit(f"错误：{run_dir}/trace.json 不存在")
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    result = leakcheck(trace, actor=actor, keywords=keywords)
    _print_result(run_dir, actor, result)
