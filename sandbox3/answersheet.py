# sandbox3/answersheet.py
"""真人测评答卷的格式（一页两用：人读 + 机读）——测评页导出与星空首页读入的合同。

- render_md(name, jd, by_dim, choices)：测评页导出时调。上半=人读（题干+四选项+✅标出真人选的，
  **不显示倾向/风险标签**，守红线"作答界面不显示标签防照标签答"）；下半=机读 ```json 块
  （schema + 真人填的名字 + 结构化 JD + 全部题目含隐藏键 + 选择映射）。
- parse_md(md)：首页吃答卷时调。抠出 ```json 块 → answers_by_dim（每题还原成
  score_dim / render_record_md 认的 a 字典：价值/问法/情景/chosen[含 dim_tendency·risk_dir]）+ jd。

诚实口径：标签只进机读 json、答卷只进 HR 侧/系统、不回流候选人；本卷未经真实结局校准、不构成预测。
live-only：解析失败大声抛 ValueError，不静默兜空。
"""
from __future__ import annotations
import json
import re

SCHEMA = "fitsandbox-answersheet-v1"

# 机读块前的哨兵注释：人一眼知道"下面别手改"，parse 也靠它+schema 双重定位
_DATA_MARK = "<!-- ↓↓ 机器数据（星空首页读它还原作答，请勿手改）↓↓ -->"


def qkey(dim_id: str, idx: int) -> str:
    """一道题的稳定键：维度 + 在该维题表里的下标（追题加的题排在后面，下标照常递增）。"""
    return f"{dim_id}#{idx}"


def render_md(name: str, jd: dict, by_dim: dict, choices: dict) -> str:
    """name=真人填的名字；jd=结构化JD；by_dim={维度:[题,...]}（题含选项的全部键）；
    choices={qkey: 选项id}。返回答卷 .md 文本。"""
    job = jd.get("职位名称", "") or jd.get("_jd_id", "岗位")
    L = [f"# 测评答卷 · {name or '（未填名）'} · {job}",
         "",
         f"> 答题人：**{name or '（未填名）'}**（真人作答）　|　出题源 JD：**{jd.get('_jd_id','')}** {job}",
         "> 题目由 AI 按这份 JD 现场生成；倾向/风险键为系统设计层、答题时对候选人隐藏（只进下方机器数据）。",
         "> 本卷未经真实结局校准、不构成对真实结局的预测；仅供 HR 侧/系统使用、不回流候选人。",
         ""]
    n = 0
    for dim_id, qs in by_dim.items():
        risk = (qs[0].get("风险") if qs else "") or ""
        L.append(f"## {risk} · {dim_id}")
        for i, q in enumerate(qs):
            n += 1
            ask = q.get("问法", "最像你")
            L.append(f'**Q{n}**（问"{ask}"）{q.get("情景","")}')
            picked = choices.get(qkey(dim_id, i))
            for o in q.get("选项", []):
                mark = " ✅" if o.get("id") == picked else "　"
                tail = "　← 你选的" if o.get("id") == picked else ""
                L.append(f'{mark} {o.get("id","")}. {o.get("文本","")}{tail}')
            L.append("")
    # —— 机读块 ——
    data = {"schema": SCHEMA, "name": name or "", "jd": jd,
            "by_dim": by_dim, "choices": choices}
    L.append(_DATA_MARK)
    L.append("```json")
    L.append(json.dumps(data, ensure_ascii=False, indent=2))
    L.append("```")
    return "\n".join(L)


_FENCE_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def parse_md(md: str) -> dict:
    """抠出含 schema 的 ```json 块 → {name, jd, by_dim, choices, answers_by_dim}。
    answers_by_dim[维度]=[{价值,问法,情景,chosen{全选项含键},why}]，直接喂 score_dim / render_record_md。
    失败大声抛 ValueError（live-only：不静默兜空）。"""
    blocks = _FENCE_RE.findall(md or "")
    data = None
    for b in blocks:
        try:
            obj = json.loads(b)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("schema") == SCHEMA:
            data = obj
            break
    if data is None:
        raise ValueError(f"答卷里找不到合法的机器数据块（schema={SCHEMA}）——这份 .md 不是测评页导出的答卷？")
    by_dim = data.get("by_dim") or {}
    choices = data.get("choices") or {}
    if not by_dim:
        raise ValueError("答卷机器数据里没有题目（by_dim 空）")

    answers_by_dim: dict[str, list] = {}
    unanswered = 0
    for dim_id, qs in by_dim.items():
        al = []
        for i, q in enumerate(qs):
            optid = choices.get(qkey(dim_id, i))
            chosen = next((o for o in q.get("选项", []) if o.get("id") == optid), None)
            if chosen is None:                       # 这题没作答/选项对不上：跳过、计一笔，不静默编一个
                unanswered += 1
                continue
            al.append({"价值": q.get("价值"), "问法": q.get("问法", "最像你"),
                       "情景": q.get("情景", ""), "chosen": chosen, "why": ""})
        if al:
            answers_by_dim[dim_id] = al
    if not answers_by_dim:
        raise ValueError("答卷里没有任何有效作答（每道题都没选/选项对不上）")
    return {"name": data.get("name", ""), "jd": data.get("jd") or {},
            "by_dim": by_dim, "choices": choices,
            "answers_by_dim": answers_by_dim, "unanswered": unanswered}
