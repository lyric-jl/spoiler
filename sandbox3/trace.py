# sandbox3/trace.py
"""把 trace 渲染成人能读的 Markdown 台本（回合制结构）。
搬运自蓝本 relate_mvp/report.py（已验证资产），改动仅限三条：
  ①头部观察主体行改为从 meta["candidate"]/meta["cast"] 生成；
  ②幕末加 relations 细目段（候选人×成员，只入档不进灯）；
  ③MVP 脚注追加"人设可为蒸馏产物"半句。
台本措辞（尤其脚注三条口径）一字不动。
"""
from __future__ import annotations
import pathlib

from .states import STATE_ENUMS, STATE_LABELS


def _beat_md(bt: dict) -> list[str]:
    out = [f"### 回合 {bt['beat']} · 行动方：{bt['acting_agent']}",
           "",
           f"**经过**：{bt['narration']}",
           "",
           f"**节骨眼**：{bt['juncture']}",
           "",
           "**候选行动**（已随机打乱顺序，括号内为 SM 原序）："]
    chosen = bt["decision"].get("action_id")
    for o in bt["options"]:
        mark = " ←★ 选择" if o["id"] == chosen else ""
        out.append(f"- **{o['id']}**（原{o['orig_id']}）. {o['text']}{mark}")
    vs = bt.get("vote_summary")
    if vs:
        rounds_s = " · ".join(f"第{v['round']}问→原{v['orig_id']}（呈现位{v['position']}）"
                              for v in bt.get("votes") or [])
        out += ["", f"**换序三问表决**：{rounds_s} ⇒ {vs['verdict']}，取原{vs['winner_orig_id']}"]
    appr = bt.get("appraisal", {})
    emo = appr.get("emotions", {})
    emo_s = "、".join(f"{k} {v}" for k, v in emo.items()
                      if isinstance(v, (int, float)) and v >= 40)
    dec = bt["decision"]
    audit = bt.get("audit", {})
    fab = audit.get("fabricated_cues") or []
    out += ["",
            f"**{bt['acting_agent']} 的内心**（情绪≥40：{emo_s or '无明显波动'}）：",
            f"> {appr.get('internal_thoughts', '（无）')}",
            "",
            f"**选择理由**（信心 {dec.get('confidence', '?')}，情绪标签：{('、'.join(dec.get('emotion_tags') or []))}）：",
            f"> {dec.get('reasoning', '')}",
            "",
            f"**理由审计**：{audit.get('verdict', '?')} —— 手册命中 {('、'.join(audit.get('playbook_match') or []) or '无')}；"
            f"与内心 {audit.get('thought_consistency', '?')}（{audit.get('thought_note', '')}）；"
            f"编造线索 {('、'.join(fab) if fab else '无')}；信息越权 {audit.get('info_overreach') or '无'}。{audit.get('note', '')}",
            "",
            f"**心口缝**（只记录不打分）：{audit.get('inner_gap') or '无'}",
            ""]
    return out


def render(trace: dict) -> str:
    m = trace["meta"]
    actors = "、".join(f"{k} {v} 次" for k, v in m.get("actor_counts", {}).items())
    vstats = m.get("vote_stats", {})
    pos_s = " ".join(f"{k}×{v}" for k, v in sorted(m.get("vote_position_counts", {}).items()))
    gaps_s = "、".join(f"{k} {v} 处" for k, v in (m.get("inner_gaps") or {}).items())

    # ① 观察主体行：从 meta["candidate"] + meta["cast"] 生成（列名单+kind）
    candidate_name = m.get("candidate", "?")
    cast_list = m.get("cast") or []
    cast_s = "、".join(f"{c['name']}（{c.get('kind', '?')}）" for c in cast_list)

    out = ["# 契合沙盘 · 受控选项推演 MVP — 台本（整改版）",
           "",
           f"- 模型：{m['model']}　幕数：{m['n_scenes']}　LLM 调用：{m['n_llm_calls']} 次　警告：{m['warnings_total']} 条",
           f"- 行动方分布：{actors or '无'}　审计黄旗：{m.get('audit_flags', 0)} 个　洗牌种子：{m.get('seed')}",
           f"- 换序三问（防位置偏置）：{vstats.get('全票', 0)} 全票 · {vstats.get('多数票', 0)} 多数票 · "
           f"{vstats.get('摇摆', 0)} 摇摆　各问选中呈现位分布：{pos_s or '无'}",
           f"- 心口缝（只记录不打分）：{gaps_s or '无'}",
           f"- 观察主体：{candidate_name}（候选人）　在场名单：{cast_s}",
           # ③ MVP 脚注追加"人设可为蒸馏产物"半句
           "- ⚠ MVP 脚注：单 run 轨迹（论文为 5 run 聚合）；人设为手写合成（人设可为蒸馏产物）；承诺估计是机制部件、未经任何对账校准，**不构成对真实结局的预测**；理由审计员也是 AI，做的是结构对账、非语义终审，黄旗供人复核。",
           ""]

    commits = []
    for sc in trace["scenes"]:
        tp = sc["turning_point"]
        scene = sc["scene"]
        out += [f"## 第 {sc['index']} 幕 · [{tp['category']}] {tp['title']}",
                "",
                f"**时间**：{sc.get('sim_time', '?')}　**在场**：{'、'.join(sc.get('witnesses') or []) or '?'}",
                "",
                f"**场景**：{scene.get('setting', '')}",
                "",
                scene.get("current_scene", ""),
                "",
                f"**冲突**：{scene.get('scene_conflict', '')}",
                ""]
        for bt in sc["beats"]:
            out += _beat_md(bt)
        out += ["**状态灯**（→ 为本幕变化）：", "", "| 状态 | 值 | 证据 |", "|---|---|---|"]
        ev = sc.get("evidence", {})
        for k in STATE_ENUMS:
            v = sc["states"][k]
            if k in sc["state_changes"]:
                a, b = sc["state_changes"][k]
                cell = f"**{a} → {b}**"
            else:
                cell = v
            out.append(f"| {STATE_LABELS[k]} `{k}` | {cell} | {ev.get(k, '')} |")
        out += ["",
                f"**留任-契合承诺**：{sc['commitment']} / 5 —— {sc['commitment_rationale']}"]
        commits.append((sc["index"], sc["commitment"]))
        cons = sc.get("consequences") or []
        if cons:
            out += ["", "**后果结算**（入台账）："]
            out += [f"- {c['matter']} → {c['outcome']}" for c in cons]

        # ② relations 细目渲染（候选人×成员，只入档不进灯）
        rels = sc.get("relations") or {}
        if rels:
            out += ["", "**关系细目**（候选人×成员，只入档不进灯）："]
            for name, rel in rels.items():
                attitude = rel.get("attitude", "?")
                evidence = rel.get("evidence", "")
                out.append(f"- {name}：{attitude}——{evidence}")
            out.append("")

        nxt = sc.get("next_tp")
        if nxt:
            out += ["", f"**挑下一幕**：状态灯触发类别 {nxt['heuristic_categories']} → "
                        f"选 `{nxt['choice']}`（{nxt['why']}）"]
        if sc["warnings"]:
            out += ["", "⚠ 本幕警告：" + "；".join(sc["warnings"])]
        out.append("")

    out += ["## 承诺轨迹", "", " → ".join(f"第{i}幕 {c}" for i, c in commits), ""]
    return "\n".join(out)


def save_run(trace: dict, out_root: pathlib.Path | None = None, jd: str = "") -> pathlib.Path:
    import json
    import time
    from .config import OUTPUT_DIR
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = (out_root or OUTPUT_DIR) / f"run_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    (out_dir / "台本.md").write_text(render(trace), encoding="utf-8")
    if jd:
        (out_dir / "jd.txt").write_text(jd, encoding="utf-8")
    return out_dir
