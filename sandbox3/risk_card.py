# sandbox3/risk_card.py
"""三风险分档判据卡（方案A · 信号分层）。
他评/客观史/沙盘行为扛分，自陈只供落差、不计分。评分全透明：每个档位都附"凭什么"。
当前实装：团队不合（其余两风险的灯映射待补）。

用法：python -m sandbox3.risk_card [--risk 团队不合] [--evidence data/evidence_zhou.json]
       [--batch output/batch_xxx]（缺省取最新批）[--out output/<batch>/判据卡-团队不合.md]

诚实口径（随卡走）：输出"高/中/低"分档判据，不是概率；沙盘状态灯的本地效度未经真实结局
校准、不构成对真实结局的预测；他评空白处标低置信，不为好看硬编满。"""
from __future__ import annotations
import argparse
import json
import pathlib

from .config import DATA_DIR, OUTPUT_DIR
from .scenes import SceneBank

# ---- 风险定义：每个风险扛分的沙盘灯 + 灯读法 + 决定性场景（沙盘要跑到才算证实/证伪）----
RISK_DEF = {
    "团队不合": {
        "lights": {
            "network": {"good": ["supportive"], "warn": ["neutral"], "bad": ["opposed", "mixed"],
                        "warn_txt": "团队接纳卡在中立、未升温", "bad_txt": "团队接纳有摩擦/被排斥"},
            "conflict": {"good": ["none", "repaired"], "warn": ["brewing"], "bad": ["active", "unresolved"],
                         "warn_txt": "冲突在酝酿", "bad_txt": "冲突爆发/未解决"},
            "repair_outcome": {"good": ["successful"], "warn": ["attempted", "none"], "bad": ["failed"],
                               "warn_txt": "修复尚未成形", "bad_txt": "修复失败"},
        },
        # 决定性场景：只有跑到这些，沙盘才真正"压"到团队不合（正面冲突对峙/社交融入/分工边界）
        "critical_scenes": {
            "C4-01": "评审会当众纠错", "C4-02": "方案里的坑", "C4-03": "被一句话否掉的方案",
            "C6-01": "已读不回", "C6-02": "缩编传闻", "C2-02": "分工灰色地带", "C1-02": "例会首秀",
        },
        "crit_gist": "正面冲突/社交融入/分工边界",
        "job_read": [
            "**独立攻坚型岗**：团队不合的实际影响**偏低**——最强的'独立交付'被岗位性质放大、团队短板被稀释。",
            "**高频跨团队/冲突中推进岗**：风险读数**偏高**——'回避正面冲突/不主动融入'正踩这类岗的命门。",
        ],
        "verify_hint": "面试/试用期重点验证：当众被否时她是据理力争还是私下消化、非正式社交里是否主动。",
    },
    "主动离职": {
        "lights": {
            "exit_marker": {"good": ["none"], "warn": ["soft"], "bad": ["hard"],
                            "warn_txt": "冒出软性去意", "bad_txt": "明确去意/被边缘化"},
            "alternatives": {"good": ["quiet"], "warn": ["salient"], "bad": ["hot"],
                             "warn_txt": "开始留意外部机会", "bad_txt": "外部机会炽热/在积极找"},
            "embeddedness": {"good": ["accrued"], "warn": ["none", "emerging"], "bad": [],
                             "warn_txt": "投入绑定未建立（试用期早期亦属正常，软信号）", "bad_txt": ""},
        },
        # 决定性场景：压到去留/被亏待/外部拉力/高压几幕，沙盘才真正"压"到主动离职
        "critical_scenes": {
            "C6-02": "缩编传闻", "C5-02": "试用期中期面谈", "C6-01": "已读不回",
            "C3-01": "周五紧急插单", "C3-03": "上线夜故障归属", "C3-02": "跨组对线",
        },
        "crit_gist": "去留抉择/被亏待/外部拉力/高压",
        "job_read": [
            "**高压/常加班/前景不明岗**：离职风险读数**偏高**——抗压、被亏待的反应、外部机会敏感正踩留人命门。",
            "**稳定/成长通道清晰岗**：实际影响**偏低**——嵌入与投入容易建立、外部拉力被对冲。",
        ],
        "verify_hint": "面试/试用期重点验证：高压插单/被忽视时她是稳住沟通还是默默看外面、对转正与发展的真实预期。",
    },
}


# ---- 测评画像 → 各风险相关维度（quiz_answer 的 9 维画像里，哪些维度扛这个风险）----
RISK_DIMS = {
    "团队不合": ["冲突应对", "协作主动性", "反馈接受", "求助与边界"],
    "主动离职": ["抗压稳定", "被忽视·不公的反应", "投入·嵌入倾向", "外部机会敏感", "尽责·可靠"],
}
_CONF_W = {"高": 1.0, "中": 0.6, "低": 0.3}      # 置信加权：低置信的维度少算


def _load_aggregate(batch: pathlib.Path | None) -> tuple[dict, str]:
    if batch is None:
        batches = sorted(OUTPUT_DIR.glob("batch_*"))
        if not batches:
            raise FileNotFoundError(f"{OUTPUT_DIR} 下没有 batch_* 聚合产物，先跑 python -m sandbox3.aggregate")
        batch = batches[-1]
    agg = json.loads((batch / "aggregate.json").read_text(encoding="utf-8"))
    return agg, batch.name


def _seen_scene_ids(agg: dict) -> set[str]:
    ids: set[str] = set()
    for row in agg.get("choices", []):
        for tp in row.get("tp_by_run", {}).values():
            ids.add(tp.split()[0])      # "C1-01 第一次接活" -> "C1-01"
    return ids


def _other_report(units: list[dict]) -> dict:
    """他评层结论：方向是否一致、跨几个独立来源。无他评时如实标'无他评'（外部候选人天生拿不到）。"""
    if not units:
        return {"verdict": "无他评", "why": "无他评证据——外部候选人，录用前他评天生拿不到",
                "up": [], "down": []}
    up = [u for u in units if u["direction"] == "+"]
    down = [u for u in units if u["direction"] == "-"]
    channels = {"面试" if "面试" in u["source"] else "背调" if "背调" in u["source"] else u["source"]
                for u in up}
    if up and len(channels) >= 2:
        verdict = "一致↑"
        why = f"{len(up)} 条指向风险，跨 {len(channels)} 个独立来源（{'、'.join(sorted(channels))}）方向一致"
    elif up and not down:
        verdict = "偏↑·单源"
        why = f"{len(up)} 条指向风险，但仅 {len(channels)} 个来源"
    elif down and not up:
        verdict = "一致↓"
        why = f"{len(down)} 条为缓冲、无指向风险的他评"
    else:
        verdict = "分歧"
        why = f"{len(up)} 条↑ / {len(down)} 条↓，他评内部不一致"
    buffer = "；缓冲：" + "、".join(u["tag"] for u in down) if down else ""
    return {"verdict": verdict, "why": why + buffer, "up": up, "down": down}


def _quiz_layer(portrait: dict | None, risk: str) -> dict:
    """测评画像层：把 quiz_answer 的相关维度倾向(低/中/高)按置信加权成一个方向。
    诚实：这是自答的行为画像（最弱那层）；低置信的维度少算。"""
    if not portrait:
        return {"verdict": "无测评", "why": "未提供测评画像", "dims": []}
    want = RISK_DIMS.get(risk, [])
    rows = [s for s in portrait.get("scores", []) if s.get("dim") in want]
    if not rows:
        return {"verdict": "无测评", "why": "测评画像未覆盖本风险的维度", "dims": []}
    wsum = sum(_CONF_W.get(s.get("confidence", "低"), 0.3) for s in rows)
    score = sum((s.get("lean") or 2.0) * _CONF_W.get(s.get("confidence", "低"), 0.3) for s in rows)
    avg = round(score / wsum, 2) if wsum else 2.0          # 1 低 ~ 3 高
    verdict = "偏↑" if avg >= 2.4 else "偏↓" if avg <= 1.6 else "中性"
    why = (f"{len(rows)} 个相关维度按置信加权 = {avg}（1 低风险~3 高风险）："
           + "、".join(f"{s['dim']} {s.get('lean_label','?')}/置信{s.get('confidence','?')}" for s in rows))
    return {"verdict": verdict, "why": why, "dims": rows, "avg": avg}


def _sandbox(agg: dict, risk: str, candidate: str) -> dict:
    """沙盘行为层：读 5-run 终值灯（众数+分布+集中度）+ 候选人心口缝 + 决定性场景覆盖。"""
    spec = RISK_DEF[risk]
    lights = agg["final_lights"]
    reads, any_bad = [], False
    for k, rule in spec["lights"].items():
        info = lights[k]
        dist, mode = info["dist"], info["mode"]
        total = sum(dist.values())
        focus = round(max(dist.values()) / total, 2)
        bad_minor = [v for v in dist if v in rule["bad"]]
        if mode in rule["bad"]:
            d, txt, any_bad = "+", rule["bad_txt"], True
        elif mode in rule["warn"]:
            d, txt = "~↑", rule["warn_txt"]
        else:
            d, txt = "-", "良性"
        if bad_minor and mode not in rule["bad"]:
            txt += f"（但 {total} 局中有 {sum(dist[v] for v in bad_minor)} 局出现 {'/'.join(bad_minor)}）"
        reads.append({"light": k, "mode": mode, "dist": dist, "focus": focus, "dir": d, "txt": txt})

    gaps = (agg.get("inner_gap_by_actor") or {}).get(candidate, 0)
    seen = _seen_scene_ids(agg)
    crit = spec["critical_scenes"]
    hit = [s for s in crit if s in seen]
    missing = [s for s in crit if s not in seen]
    covered = len(missing) == 0

    if any_bad:
        verdict = "印证↑"
    elif all(r["dir"] == "-" for r in reads):
        verdict = "印证↓" if covered else "良性·但关键场景未覆盖"
    else:
        verdict = "弱混合" if covered else "弱混合·关键场景未覆盖"
    return {"verdict": verdict, "reads": reads, "gaps": gaps,
            "covered": covered, "hit": hit, "missing": missing, "crit": crit,
            "n_runs": agg.get("n_runs")}


def _objective(units: list[dict]) -> dict:
    up = [u for u in units if u["direction"] == "+"]
    unknown = [u for u in units if u["direction"] == "0"]
    return {"up": up, "unknown": unknown}


def _band(other: dict, quiz: dict, sand: dict) -> tuple[str, str]:
    """分档（透明规则）：有他评→他评定大方向、沙盘证实/打折；无他评→测评画像+沙盘，且不轻易判高。"""
    ov, sv, qv = other["verdict"], sand["verdict"], quiz["verdict"]
    if ov == "无他评":
        if sv == "印证↑":
            return "中", "无他评；沙盘行为现风险指向，但缺他评这层最硬证据，不轻易判高"
        if qv == "偏↓" and sv in ("印证↓", "良性·但关键场景未覆盖"):
            return "低", "无他评；测评画像偏低风险、沙盘行为也未现风险"
        if qv == "偏↑":
            return "中", "无他评；测评画像偏高风险，但仅自答一层、沙盘未印证，封顶到中"
        return "中", "无他评；测评中性/沙盘未压到，证据不足以定高低"
    if ov == "一致↑":
        if sv == "印证↑":
            return "高", "他评一致指向风险，且沙盘行为印证"
        if sv in ("印证↓", "良性·但关键场景未覆盖"):
            return "中", ("他评两方一致指向风险，但已跑的场景里沙盘行为反而良性——他评与行为分歧；"
                          "且最硬的场景（当众无缓冲被否 / 社交融入）尚未跑到，未压到命门，故不轻易翻成低")
        return "中", "他评两方一致指向风险，沙盘弱混合/未覆盖——行为既未证实也未证伪"
    if ov == "一致↓" and sv in ("印证↓", "良性·但关键场景未覆盖"):
        return "低", "他评为缓冲、沙盘行为也未现风险"
    if ov in ("偏↑·单源", "分歧"):
        return "中", "他评证据偏弱或不一致，单凭现有材料不足以定高/低"
    return "中", "证据组合落在中间区"


def _confidence(other: dict, quiz: dict, sand: dict, obj: dict) -> tuple[str, str]:
    reasons = []
    no_other = other["verdict"] == "无他评"
    strong = other["verdict"] == "一致↑"
    if no_other:
        reasons.append("无他评——最硬的那层缺失（−−）")
    else:
        reasons.append("他评两方一致（+）" if strong else f"他评{other['verdict']}（弱）")
    if quiz["dims"]:
        cs = [d.get("confidence") for d in quiz["dims"]]
        reasons.append(f"测评画像 {cs.count('高')}高/{cs.count('中')}中/{cs.count('低')}低（自答层、弱）")
    if sand["covered"]:
        reasons.append("决定性场景已覆盖（+）")
    else:
        reasons.append(f"决定性场景 {len(sand['hit'])}/{len(sand['crit'])} 跑到、缺行为印证（−）")
    if obj["unknown"]:
        reasons.append("背调对关键维度标'未知'（−）")
    if no_other:                                   # 无他评天生薄：封顶到中、未覆盖则低（红线：薄就低置信）
        level = "中" if (sand["covered"] and quiz["dims"]) else "低"
    elif strong and sand["covered"]:
        level = "高"
    elif strong:
        level = "中"
    else:
        level = "低"
    return level, "；".join(reasons)


def build_card(risk: str, evidence: dict | None, agg: dict, batch_name: str,
               portrait: dict | None = None) -> dict:
    units = (evidence or {}).get("risks", {}).get(risk, {})
    cand = ((evidence or {}).get("candidate") or (portrait or {}).get("name") or "候选人")
    other = _other_report(units.get("他评", []))
    quiz = _quiz_layer(portrait, risk)
    sand = _sandbox(agg, risk, cand)
    obj = _objective(units.get("客观史", []))
    band, band_why = _band(other, quiz, sand)
    conf, conf_why = _confidence(other, quiz, sand, obj)
    return {"candidate": cand, "risk": risk, "batch": batch_name, "band": band,
            "band_why": band_why, "confidence": conf, "conf_why": conf_why,
            "other": other, "quiz": quiz, "sandbox": sand, "objective": obj,
            "self_ref": units.get("自陈_参考", [])}


def render_card(card: dict) -> str:
    s, c = card["sandbox"], card
    band_icon = {"高": "🔴 高", "中": "🟡 中", "低": "🟢 低"}[c["band"]]
    o = [f"# 风险判据卡 · {c['risk']}", "",
         f"**候选人：{c['candidate']}　风险维度：{c['risk']}　数据：{c['batch']}（{s['n_runs']}-run）**", "",
         f"## 判据：{band_icon}　置信度：{c['confidence']}", "",
         f"- **档位依据**：{c['band_why']}",
         f"- **置信依据**：{c['conf_why']}", "",
         "> 这是分档判据（不是概率）。沙盘灯未经真实结局校准、不构成预测；落差只描述不打分。", "",
         "## 证据拆解", "",
         "**① 他评层（扛分）** — " + c["other"]["verdict"] + "：" + c["other"]["why"], ""]
    for u in c["other"]["up"] + c["other"]["down"]:
        mark = "↑" if u["direction"] == "+" else "↓"
        o.append(f"- [{mark}] {u['source']}（{u['file']}）：「{u['quote']}」")
    q = c.get("quiz", {})
    o += ["", "**①′ 测评画像层（自答行为画像·弱）** — " + q.get("verdict", "无测评") + "：" + q.get("why", "")]
    o += ["", "**② 沙盘行为层（扛分）** — " + s["verdict"] + f"；候选人心口缝 {s['gaps']} 处（行动比内心更回避，间接印证）", ""]
    for r in s["reads"]:
        dist = "、".join(f"{k}×{v}" for k, v in r["dist"].items())
        o.append(f"- [{r['dir']}] {r['light']}：众数 **{r['mode']}**（{dist}；集中度 {r['focus']}）→ {r['txt']}")
    if s["missing"]:
        miss = "、".join(f"{sid}（{s['crit'][sid]}）" for sid in s["missing"])
        o += ["", f"- ⚠ **决定性场景未跑到（{len(s['missing'])}/{len(s['crit'])}）**：{miss}",
              f"  → 这几幕才真正压'{RISK_DEF[c['risk']]['crit_gist']}'；没跑到，沙盘只能说'未证实'，故压低置信。"]
    o += ["", "**③ 客观史层** — " + ("、".join(u["tag"] for u in c["objective"]["up"]) or "无") +
          ("；缺口：" + "、".join(u["tag"] for u in c["objective"]["unknown"]) if c["objective"]["unknown"] else ""), ""]
    o += ["**④ 自陈层（仅供落差，不计分）**", ""]
    for u in c["self_ref"]:
        o.append(f"- {u['source']}（{u['file']}）：「{u['quote']}」—— {u['tag']}")
    rd = RISK_DEF[c["risk"]]
    o += ["", "## 对岗位读数（同一证据，换岗位结论就翻）", ""]
    o += [f"- {line}" for line in rd["job_read"]]
    o += ["", "## 建议（把'中'升级为'高置信'要做什么）", ""]
    if s["missing"]:
        o.append("- 跑一组**定向场景**补行为印证："
                 + "、".join(f"{sid}（{s['crit'][sid]}）" for sid in s["missing"][:4]) + " 等；")
    o += [f"- {rd['verify_hint']}", ""]
    return "\n".join(o)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--risk", default="团队不合", choices=list(RISK_DEF))
    ap.add_argument("--evidence", default=None, help="他评/客观史 JSON（外部候选人可不给）")
    ap.add_argument("--portrait", default=None, help="quiz_answer 出的 画像.json（测评画像层）")
    ap.add_argument("--batch", default=None, help="output/batch_xxx 目录；缺省取最新批")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    evidence = (json.loads(pathlib.Path(args.evidence).read_text(encoding="utf-8"))
                if args.evidence else None)
    portrait = (json.loads(pathlib.Path(args.portrait).read_text(encoding="utf-8"))
                if args.portrait else None)
    agg, batch_name = _load_aggregate(pathlib.Path(args.batch) if args.batch else None)
    card = build_card(args.risk, evidence, agg, batch_name, portrait)
    md = render_card(card)

    out = pathlib.Path(args.out) if args.out else (OUTPUT_DIR / batch_name / f"判据卡-{args.risk}.md")
    out.write_text(md, encoding="utf-8")
    print(f"判据：{card['band']}　置信：{card['confidence']}")
    print(f"判据卡已写出：{out}")


if __name__ == "__main__":
    main()
