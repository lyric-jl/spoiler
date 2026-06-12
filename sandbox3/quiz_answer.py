# sandbox3/quiz_answer.py
"""模拟答题 + 计分→维度画像：候选人 persona 答 quiz_gen 出的卷 → 9 维倾向+置信 + 作答记录。

诚实口径（随产物走）：答案是编剧模型 **扮演**给定 persona 的"猜答"、非真人作答（刻意与沙盘演员
不同源，免得"自陈 vs 行为"的落差变成同一模型自说自话）；本模块跑通的是
"测评→画像"这一接，**不构成对真实作答/真实结局的预测**。置信=同维多题作答稳定度（spec 形态1：飘则低）。
答题时**对模型隐藏选项的维度键/风险键**（只给题干+选项文本），避免它照标签作弊。live-only。

命令：python -m sandbox3.quiz_answer --quiz output/quiz_xxx/卷.json --cv data/cv_samples/CV1_林女士.json
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys
import time

from .config import OUTPUT_DIR
from .llm import LLMClient

RISK_VAL = {"低": 1.0, "中": 2.0, "中高": 2.5, "高": 3.0}
LEAN_LABEL = {1: "低", 2: "中", 3: "高"}

ANSWER_SYSTEM = """你要**扮演一位真实求职者本人**来作答一份情境测评。规矩：
1. 完全代入这个人的性格、习惯、处境，按"你真实会怎么做"选——不是按"哪个看起来好"选，别挑漂亮答案。
2. 每题只能选一个选项（A/B/C/D）。注意问法：问"最像你"就选最贴你本能的；问"最不像你"就选你最不会做的那一个。
3. 只输出 JSON：{"choice": "A/B/C/D 之一", "why": "一句话理由，用'我…'的第一人称"}。"""


def persona_block(cv: dict) -> str:
    name = cv.get("姓名", "该候选人")
    jobs = cv.get("工作/实习经历") or []
    cur = jobs[0] if isinstance(jobs, list) and jobs else {}
    youshi = (cv.get("个人优势") or "").replace("\n", " ")
    desc = (cur.get("工作描述") or "") if isinstance(cur, dict) else ""
    return "\n".join([
        f"你是{name}，{cv.get('性别','')}，{cv.get('年龄','')}，{cv.get('工作年限','')}工作经验，"
        f"{cv.get('最高学历','')}学历，现居{cv.get('现居地址','')}，目前状态：{cv.get('求职状态','')}。",
        f"你最近的工作：{cur.get('公司','') if isinstance(cur, dict) else ''} "
        f"{cur.get('职位名称','') if isinstance(cur, dict) else ''}"
        f"（{cur.get('在职时间','') if isinstance(cur, dict) else ''}）。{desc[:200]}",
        f"你的自我认知与优势：{youshi[:260]}",
        "下面是一份针对某岗位的情境测评。请完全代入你本人的真实性格与处境作答——按你真的会怎么做选。",
    ])


def answer_one(client: DeepSeekClient, persona: str, q: dict) -> dict:
    # 只给 id+文本，隐藏 dim_tendency/risk_dir，防模型照标签作弊
    opts = q.get("选项", [])
    opts_txt = "\n".join(f"{o.get('id')}. {o.get('文本','')}" for o in opts)
    ask = q.get("问法", "最像你")
    user = (f"{persona}\n\n【情境】{q.get('情景','')}\n"
            f"问：下面哪个**{ask}**？\n{opts_txt}\n\n只输出 JSON。")
    out = client.complete_json(ANSWER_SYSTEM, user, temperature=0.7, max_tokens=400)
    cid = (out.get("choice") or "").strip()[:1].upper()
    why = out.get("why", "")
    chosen = next((o for o in opts if o.get("id") == cid), None)
    if chosen is None:                       # 模型给了非法 choice：兜底取首项、明着标，不静默
        chosen = opts[0]
        cid = chosen.get("id")
        why = "〔答案非法已兜底〕" + why
    return {"choice": cid, "why": why, "chosen": chosen,
            "价值": q.get("价值"), "问法": ask, "情景": q.get("情景", "")}


def score_dim(dim_id: str, risk: str, ans_list: list[dict]) -> dict:
    """全好题选中项=她的倾向（risk_dir 越高越偏风险端）；全坏题选中=她最排斥的坏法（反向信号，单列）。
    置信=全好题内部一致度（极差小=稳=高置信，spec 形态1）。
    追题语境补充（2026-06-12）：极差是"一票否决"——答过一次极端就永远洗不掉，追题会沦为走过场。
    故 ≥4 题（只有追题后才到得了）时看"多数"：多数答案聚在一处、只有早先离群的，按多数升"中"；
    但曾飘过不给"高"（诚实封顶）。"""
    good = [a for a in ans_list if a["价值"] == "全好"]
    bad = [a for a in ans_list if a["价值"] == "全坏"]
    good_vals = [RISK_VAL.get((a["chosen"].get("risk_dir") or "").strip(), 2.0) for a in good]
    lean = round(sum(good_vals) / len(good_vals), 2) if good_vals else None
    lean_label = LEAN_LABEL.get(round(lean)) if lean is not None else "未知"
    if len(good_vals) >= 2:
        spread = max(good_vals) - min(good_vals)
        conf = "高" if spread <= 0.5 else "中" if spread <= 1.0 else "低"
        if conf == "低" and len(good_vals) >= 4:
            med = sorted(good_vals)[len(good_vals) // 2]
            share = sum(1 for v in good_vals if abs(v - med) <= 0.5) / len(good_vals)
            if share >= 0.75:
                conf = "中"                  # 多数稳、个别离群：升中不升高
    elif good_vals:
        conf = "中"                          # 单题，证据薄
    else:
        conf = "低"
    return {
        "dim": dim_id, "risk": risk, "lean": lean, "lean_label": lean_label, "confidence": conf,
        "n_good": len(good), "n_bad": len(bad),
        "good_picks": [{"tend": a["chosen"].get("dim_tendency"),
                        "risk_dir": a["chosen"].get("risk_dir"), "why": a["why"]} for a in good],
        "rejects": [{"tend": a["chosen"].get("dim_tendency"),
                     "risk_dir": a["chosen"].get("risk_dir"), "why": a["why"]} for a in bad],
    }


def render_portrait_md(cv: dict, jd: dict, scores: list[dict]) -> str:
    L = [f"# 测评维度画像 · {cv.get('姓名','')}（模拟作答）", "",
         f"> 出题源 JD：**{jd.get('_jd_id','')}** {jd.get('职位名称','')}；答题人：**{cv.get('姓名','')}**"
         f"（{cv.get('_cv_id','')} 虚构脱敏简历）。",
         "> ⚠ 答案是 DeepSeek **扮演**该候选人的猜答、**非真人作答**；本表是"
         "\"测评→画像\"机制的产物，**不构成对真实作答/真实结局的预测**。",
         "> 倾向＝她全好题选中项的风险端均值（低/中/高）；置信＝同维全好题作答稳定度（飘则低）；"
         "题量列带「追N轮」＝作答飘、系统自适应追题的轨迹（追满仍飘则诚实判低）。", "",
         "| 风险 | 维度 | 倾向 | 置信 | 题量（追题） | 她最像的做法（全好选中） | 她最排斥的坏法（全坏选中） |",
         "|---|---|---|---|---|---|---|"]
    for s in scores:
        likes = "；".join(p["tend"] or "" for p in s["good_picks"]) or "—"
        rej = "；".join(r["tend"] or "" for r in s["rejects"]) or "—"
        lean = f"{s['lean_label']}（{s['lean']}）" if s["lean"] is not None else "未知"
        nq = s.get("n_questions", s["n_good"] + s["n_bad"])
        pr = s.get("probe_rounds", 0)
        probe = f"{nq} 题（追{pr}轮：{'→'.join(s.get('probe_trail', []))}）" if pr else f"{nq} 题"
        L.append(f"| {s['risk']} | {s['dim']} | {lean} | {s['confidence']} | {probe} | {likes} | {rej} |")
    L += ["", "> 读法：倾向是「她答出来的样子」、不是「她真的风险有多高」——后者要等沙盘外推 + 真实结局校准（见 risk_card / spec §4）。"]
    return "\n".join(L)


def render_record_md(cv: dict, jd: dict, answers_by_dim: dict) -> str:
    """供蒸馏器读：把她每题的选择当作"行为证据"（她面对X→选了Y、理由Z）。"""
    L = [f"# 测评作答记录 · {cv.get('姓名','')}（模拟作答，供蒸馏）", "",
         f"> 答题人：{cv.get('姓名','')}（{cv.get('_cv_id','')}，虚构脱敏）。记录她在每个情境下的"
         "**选择=行为倾向**，供蒸馏成人设+行为手册。答案系 DeepSeek 扮演其作答、非真人。", ""]
    for dim_id, al in answers_by_dim.items():
        L.append(f"## {dim_id}")
        for a in al:
            ask = "最像她" if a["问法"] == "最像你" else "最不像她"
            L.append(f"- 情境：{a['情景']}")
            L.append(f"  → {ask}的选择：{a['chosen'].get('文本','')}（她说：{a['why']}）")
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="模拟答题+计分→维度画像（测评→画像这一接）")
    ap.add_argument("--quiz", required=True, help="quiz_gen 出的 卷.json 路径")
    ap.add_argument("--cv", required=True, help="data/cv_samples 下的候选人 json")
    args = ap.parse_args(argv)

    quiz = json.loads(pathlib.Path(args.quiz).read_text(encoding="utf-8"))
    cv = json.loads(pathlib.Path(args.cv).read_text(encoding="utf-8"))
    jd = quiz.get("jd", {})
    by_dim = quiz.get("by_dim", {})
    if not by_dim:
        raise SystemExit(f"{args.quiz} 里没有 by_dim（题目）")

    persona = persona_block(cv)
    client = LLMClient("writer")
    answers_by_dim: dict[str, list] = {}
    scores: list[dict] = []
    for i, (dim_id, qs) in enumerate(by_dim.items(), 1):
        risk = qs[0].get("风险", "") if qs else ""
        print(f"[{i}/{len(by_dim)}] {cv.get('姓名','')} 答题：{dim_id}（{len(qs)} 题）…", file=sys.stderr)
        al = [answer_one(client, persona, q) for q in qs]
        answers_by_dim[dim_id] = al
        scores.append(score_dim(dim_id, risk, al))

    stamp = time.strftime("%Y%m%d-%H%M%S")
    outdir = OUTPUT_DIR / f"answer_{cv.get('_cv_id','CV')}_{stamp}"
    (outdir / "材料").mkdir(parents=True, exist_ok=True)
    (outdir / "画像.json").write_text(
        json.dumps({"cv_id": cv.get("_cv_id"), "name": cv.get("姓名"),
                    "jd_id": jd.get("_jd_id"), "scores": scores},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "画像.md").write_text(render_portrait_md(cv, jd, scores), encoding="utf-8")
    # 作答记录单独落在 材料/ 子目录，供蒸馏器 glob（避免把"画像"这层我们的解读也喂回蒸馏）
    (outdir / "材料" / "测评作答记录.md").write_text(
        render_record_md(cv, jd, answers_by_dim), encoding="utf-8")

    print(f"\n写出：{outdir}\\画像.md（+ 材料/测评作答记录.md 供蒸馏）", file=sys.stderr)
    print(render_portrait_md(cv, jd, scores))


if __name__ == "__main__":
    main()
