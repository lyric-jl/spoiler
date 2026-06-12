# sandbox3/quiz_gen.py
"""测评卷出题器（AIG）：JD + 目标维度 + 价值（全好/全坏）→ 编剧模型生成情境迫选题。

这是"AI 按 JD 自动出迫选题"产品能力的最小实现。出题走编剧模型（config.ROLES writer，
中文文笔档），live-only，失败大声抛/标，绝不用假题冒充。

设计依据：契合沙盘-测评卷设计spec-20260608.md（9 维＝团队不合4+离职5、情境迫选、全好~70%/全坏~30%、
两层答案键）。团队不合 4 维带"金标题"few-shot 锚质量；离职 5 维暂无金标题（照实标）。

命令：python -m sandbox3.quiz_gen [--jd JD158_新媒体运营经理] [--good 2] [--bad 1]
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys
import time

from .config import DATA_DIR, OUTPUT_DIR, ROLES
from .llm import LLMClient, LLMError

JD_DIR = DATA_DIR / "jd_samples"

# ---- 8 维度（spec §1）。axis=倾向轴；tendencies=该维 dim_tendency 候选标签(低→高风险排序，
#      防止模型照抄 JSON 模板里的示例标签串味)；prior=风险先验方向；anchor 仅供把握构念、不写进题 ----
DIMENSIONS = [
    {"id": "冲突应对", "risk": "团队不合",
     "axis": "你的方案/观点被同事否定或质疑时怎么应对：建设性对峙摆数据 / 回避私下 / 拖延迂回 / 顺从退让",
     "tendencies": "建设性对峙(低) / 回避私下(中) / 拖延迂回(中) / 顺从退让(高)",
     "prior": "高'回避/顺从/拖延'→团队不合风险↑（本维聚焦'观点/方案分歧'，与'反馈接受'的被批评区分）",
     "anchor": "关系冲突→团队绩效与满意↓(De Dreu & Weingart 2003，已核)"},
    {"id": "协作主动性", "risk": "团队不合",
     "axis": "主动共享/求援/融入 ↔ 独来独往、只管自己那摊",
     "tendencies": "主动外扩(低) / 半主动响应(中) / 被动等问(中) / 独来独往(高)",
     "prior": "低主动→团队不合风险↑",
     "anchor": "大五外向/宜人性"},
    {"id": "反馈接受", "risk": "团队不合",
     "axis": "你的工作/错误被(当众)批评纠正时：复盘接受 / 防御推因 / 表面接受暗里记仇 / 退缩内化",
     "tendencies": "复盘接受(低) / 防御推因(中高) / 表面接受暗里记仇(高) / 退缩内化(中高)",
     "prior": "防御/记仇/退缩→团队不合风险↑（本维聚焦'被批评纠错'，与'冲突应对'的观点分歧区分）",
     "anchor": "大五宜人性（被批评时的合作反应）"},
    {"id": "求助与边界", "risk": "团队不合",
     "axis": "卡住时开口求助 ↔ 硬扛不吭声；灰色活/越界请求接不接、怎么接",
     "tendencies": "守边界·走流程(低) / 柔性拒绝(中) / 无条件承接(中) / 隐忍记账(中高) / 硬扛不求助(高)",
     "prior": "硬扛+边界模糊(隐忍记账)→团队不合风险↑",
     "anchor": "样本驱动（周默手册最强信号）；构念上贴 大五宜人(难拒绝/过度承接)+求助回避，正式锚待补"},
    {"id": "抗压稳定", "risk": "主动离职",
     "axis": "高压/插单/加班下：稳住推进 / 退缩回避 / 情绪外溢",
     "tendencies": "稳住推进(低) / 求助调配(低) / 退缩回避(高) / 情绪外溢(高)",
     "prior": "退缩/外溢→主动离职风险↑",
     "anchor": "情绪稳定→离职意向(Zimmerman 2008)"},
    {"id": "被忽视·不公的反应", "risk": "主动离职",
     "axis": "被忽视/分配不公/功劳被抢时怎么反应：当面沟通争取 / 忍下不说 / 消极对抗(撂挑子·阴阳) / 积怨憋着想走",
     "tendencies": "沟通争取(低) / 忍下不说(中) / 消极对抗(中高) / 积怨想走(高)",
     "prior": "不公感积压(忍/消极对抗/积怨)→主动离职风险↑（聚焦'对内的不公反应'，与'外部机会敏感'的外部拉力区分）",
     "anchor": "组织公正感→离职意向↓(Cohen-Charash & Spector 2001，已核；量表 Colquitt 2001)"},
    {"id": "投入·嵌入倾向", "risk": "主动离职",
     "axis": "扎根建关系/主动拿专属活/融进团队 ↔ 保持抽离、把这当跳板",
     "tendencies": "主动扎根(低) / 本分完成(中) / 保持抽离(高) / 只当跳板(高)",
     "prior": "抽离→主动离职风险↑",
     "anchor": "工作嵌入性(Jiang 2012)"},
    {"id": "外部机会敏感", "risk": "主动离职",
     "axis": "遇到更好的外部机会(更高薪/更近/更稳)时多容易动心、多快行动",
     "tendencies": "安于现状(低) / 看看不动(中) / 容易动心(中高) / 主动骑驴找马(高)",
     "prior": "高敏感→主动离职风险↑",
     "anchor": "离职史/hobo 效应(Judge & Watanabe 1995)"},
    {"id": "尽责·可靠", "risk": "主动离职",
     "axis": "答应的活/交付质量：有始有终、主动收尾抠细节 ↔ 挑肥拣瘦、差不多就交、烂尾甩手",
     "tendencies": "有始有终·主动收尾(低) / 按标准交差(低) / 挑活躲麻烦(中) / 差不多就交·不复核(中高) / 烂尾甩锅(高)",
     "prior": "低尽责(挑活/糊弄/烂尾)→实际离职风险↑；兼照'能干但不好好干'的不胜任信号",
     "anchor": "尽责性→实际离职(Zimmerman 2008，已核)；尽责→工作绩效(大五最稳预测项·数待核)"},
]

# ---- 金标题（few-shot）：团队不合 4 维各 1 道，取自 Opus 手生成样题，锚住目标质量 ----
GOLDEN = {
    "冲突应对": (
        "情景：周会上你提的接口优化方案，被资深同事一句\"这思路三年前试过、扛不住并发\"否掉、"
        "没给细节——而你手里有压测数据。问：最像你的做法？\n"
        "A. 当场调出压测数据，请他说说当年具体哪个环节扛不住。[建设性对峙·低]\n"
        "B. 当场点头\"我再核对下\"，会后私下找他要细节。[回避私下·中]\n"
        "C. 当场先不接，把数据整理成文档，下次周会正式提。[迂回拖延·中]\n"
        "D. 那先按他的来，真遇到并发瓶颈再说。[顺从·有理也不争=被动·高]"
    ),
    "反馈接受": (
        "（全坏题示范）情景：评审会上组长当众指出你一个低级错误，措辞挺直接，会议室一时安静。"
        "问：最不像你的是？（4 个都是瑕疵反应，他排除的'最不像'反推阴影面）\n"
        "A. 当场解释这块需求文档本就没写清，不全怪自己。[推因]\n"
        "B. 表面应\"好的我改\"，心里把\"当众这么说\"记一笔。[记仇]\n"
        "C. 沉默低头，会后谁也不说、自己闷头改。[退缩内化]\n"
        "D. 嘴上认了，之后几天对组长明显冷淡。[消极对抗]"
    ),
    "协作主动性": (
        "情景：你刚搞定一个别人踩过的依赖坑、记了详细笔记，正好看到隔壁组新人卡在同一个坑。"
        "问：最像你的做法？\n"
        "A. 主动走过去把笔记给他、顺手帮看一眼。[主动外扩·低]\n"
        "B. 在团队群发份\"踩坑笔记\"，谁要自取。[半主动·中]\n"
        "C. 他来问我肯定说；不问就先忙自己的。[被动响应·中]\n"
        "D. 先把自己手头活推完，有空再说。[独来独往·高]"
    ),
    "求助与边界": (
        "情景：老员工 IM 甩来\"订单回滚那接口归属一直没定，你新人顺手弄一下呗\"——这活在分工文档里"
        "确实是灰色地带。问：最像你的做法？\n"
        "A. 先问清\"这块算谁的\"，让组长定了再接。[守边界·走流程·低]\n"
        "B. 二话不说先接，卖个人情。[无条件承接·易被压垮·中]\n"
        "C. 接是接，但心里记着\"这是帮忙、不是我的活\"。[隐忍记账·被忽视会爆·中高]\n"
        "D. 委婉推回\"我排期满了，你问问组长？\"。[柔性拒绝·中]"
    ),
}

SYSTEM = """你是资深职场测评出题专家，专长情境判断测验(SJT)里的"情境迫选"题。\
你给一家公司的某个真实岗位(JD)出题，用于在录用前筛查候选人的"团队不合 / 主动离职"风险倾向。

铁律（违反即作废）：
1. 情景必须长在这份 JD 的真实工作场景上——用 JD 里写到的团队规模、汇报关系、跨部门对象、\
典型任务、这个岗位真会遇到的冲突/压力。禁止放之四海皆准的空泛情景（如"你和同事吵架了"这种没有岗位质感的）。
2. 一道题给 4 个互斥选项，各对应"目标维度"倾向轴上的一种典型反应（我会给你这条轴）。
3. 社会赞美度配平（这是迫选题的命门）：
   - 全好题：4 个选项都得是"说得过去的专业做法"，不能有一眼可见的标准答案，让人难取舍；问"最像你"。考的是他在好做法之间的内部优先级。
   - 全坏题：4 个选项**全部**是有瑕疵的失败反应（risk_dir 必须都是 中或高，**严禁任何健康/低风险选项混入**——这是全坏题最常见的翻车点）；靠变化"触发情境或表现形式"区分这 4 个坏反应、不是靠好坏程度；问"最不像你"（逆反小、信息照拿）。
4. 每个选项必须标注两个键：dim_tendency=它落在倾向轴的哪一种（用简短中文标签）；risk_dir=该选项的风险先验方向（只能填 低/中/高 之一）。
5. 选项要口语、具体、像真人会做的事，别写贴标签的空话；4 个选项长度相近。
6. 只输出 JSON，不要任何解释性文字。"""

USER_TMPL = """【岗位 JD（真实脱敏数据）】
职位名称：{职位名称}
职类：{职类名称}　薪资：{薪资}　年限：{年限要求}　学历：{学历要求}　城市：{城市要求}
职位关键词：{职位关键词}
职位描述：
{职位描述}

【目标维度】{id}（风险类：{risk}）
倾向轴：{axis}
风险先验方向：{prior}
研究构念锚点（仅帮你把握方向，别写进题面）：{anchor}

【dim_tendency 只能从本维度这份菜单里取（括号是该反应对应的 risk_dir）】
{tendencies}
全好题：4 个选项尽量覆盖菜单里不同的反应，至少含 1 个"低"和 1 个偏高的；\
全坏题：4 个选项**全部**取中/高风险的失败模式（risk_dir 都不许是"低"、不许混健康选项），靠变化"触发情境/表现形式"让 4 个坏反应彼此不同、别重复。

【选项硬要求】每题必须 4 个选项 A/B/C/D，每个"文本"**15–40 字、彼此长度接近**，\
口语具体；**严禁任何选项文本为空或只写省略号**——四个都要写满。

【本批要出】{n_good} 道全好题（问"最像你"）+ {n_bad} 道全坏题（问"最不像你"）。

{golden}
【严格按此 JSON 输出】（下面 dim_tendency/risk_dir 是占位，按本维度菜单填，别照抄）
{{
  "questions": [
    {{
      "维度": "{id}",
      "风险": "{risk}",
      "价值": "全好",
      "问法": "最像你",
      "情景": "（贴岗的具体职场情景，1-3 句）",
      "选项": [
        {{"id": "A", "文本": "……", "dim_tendency": "<本维度菜单里的低风险反应>", "risk_dir": "低"}},
        {{"id": "B", "文本": "……", "dim_tendency": "<菜单里的反应>", "risk_dir": "中"}},
        {{"id": "C", "文本": "……", "dim_tendency": "<菜单里的反应>", "risk_dir": "中"}},
        {{"id": "D", "文本": "……", "dim_tendency": "<菜单里的高风险反应>", "risk_dir": "高"}}
      ]
    }}
  ]
}}"""


def _golden_block(dim_id: str) -> str:
    g = GOLDEN.get(dim_id)
    if not g:
        return "（本维度暂无金标题样板，请你按上面铁律自行把握质量。）\n"
    return "【金标题样板（照这个质量与风格出，但情景要换成贴本 JD 的新情景，不要照抄）】\n" + g + "\n"


def load_jd(name: str) -> dict:
    """name 可带或不带 .json；也可给完整路径。"""
    p = pathlib.Path(name)
    if not p.exists():
        p = JD_DIR / (name if name.endswith(".json") else name + ".json")
    if not p.exists():
        avail = sorted(x.stem for x in JD_DIR.glob("*.json")) if JD_DIR.exists() else []
        raise SystemExit(f"找不到 JD：{name}。可用：{avail}")
    return json.loads(p.read_text(encoding="utf-8"))


def _bad_questions(qs) -> str:
    """返回不合格原因（空串=合格）。质量闸：每题须 4 个非空选项。"""
    if not isinstance(qs, list) or not qs:
        return "没有 questions 列表"
    for i, q in enumerate(qs, 1):
        opts = q.get("选项", [])
        if len(opts) != 4:
            return f"第{i}题选项数={len(opts)}≠4"
        for o in opts:
            if len((o.get("文本") or "").strip()) < 4:
                return f"第{i}题有空/过短选项：{o.get('id')}"
    return ""


def _bad_leak(qs) -> str:
    """全坏题专项闸：全坏题里出现 risk_dir='低'（健康选项漏入）即不合格。返回原因（空串=没漏）。"""
    for i, q in enumerate(qs, 1):
        if q.get("价值") != "全坏":
            continue
        for o in q.get("选项", []):
            if (o.get("risk_dir") or "").strip() == "低":
                return f"第{i}题(全坏)混入健康选项 {o.get('id')}"
    return ""


def gen_dimension(client: LLMClient, jd: dict, dim: dict,
                  n_good: int, n_bad: int, tries: int = 3) -> list[dict]:
    user = USER_TMPL.format(
        职位名称=jd.get("职位名称", ""), 职类名称=jd.get("职类名称", ""),
        薪资=jd.get("薪资", ""), 年限要求=jd.get("年限要求", ""),
        学历要求=jd.get("学历要求", ""), 城市要求=jd.get("城市要求", ""),
        职位关键词=jd.get("职位关键词", ""), 职位描述=jd.get("职位描述", ""),
        id=dim["id"], risk=dim["risk"], axis=dim["axis"],
        tendencies=dim["tendencies"], prior=dim["prior"], anchor=dim["anchor"],
        n_good=n_good, n_bad=n_bad, golden=_golden_block(dim["id"]),
    )
    last = ""
    fallback = None  # 结构合格但全坏题漏健康选项的版本，留作"降级只出全好"的底，别连全好一起废
    for attempt in range(tries):
        out = client.complete_json(SYSTEM, user, temperature=0.85, max_tokens=4000)
        qs = out.get("questions")
        why = _bad_questions(qs)
        if why:
            last = why
            print(f"    维度[{dim['id']}]第{attempt + 1}次结构不合格（{why}），重试", file=sys.stderr)
            continue
        leak = _bad_leak(qs)
        if not leak:
            return qs
        fallback, last = qs, leak
        print(f"    维度[{dim['id']}]第{attempt + 1}次{leak}，重试", file=sys.stderr)
    # 退出重试：若有"结构合格但全坏漏健康"的版本，降级为只保留全好题（这类'健康反应天然在一端'的维度全坏难出）
    if fallback is not None:
        good_only = [q for q in fallback if q.get("价值") != "全坏"]
        if good_only:
            print(f"    维度[{dim['id']}]全坏题{tries}次去不掉健康选项→降级为只出全好"
                  f"（保留 {len(good_only)} 题、丢 {len(fallback) - len(good_only)} 道全坏）", file=sys.stderr)
            return good_only
    raise LLMError(f"维度[{dim['id']}]{tries}次仍出不合格题（{last}）——不放空题混过")


def render_md(jd: dict, by_dim: dict, failed: list[str]) -> str:
    lines = [f"# 测评卷（AIG 真跑·编剧模型出题）· {jd.get('职位名称','')}",
             "",
             f"> 出题源 JD：**{jd.get('_jd_id','')}** {jd.get('职位名称','')}"
             f"（{jd.get('职类名称','')}／{jd.get('城市要求','')}／{jd.get('薪资','')}）——"
             f"{jd.get('_源','真实脱敏数据')}",
             f"> 出题模型：**{ROLES['writer'][1]}（编剧工种，产品自家栈）**；设计依据 spec=契合沙盘-测评卷设计spec-20260608.md。",
             "> 键说明：`dim_tendency`=维度倾向（设计层，现可用）／`risk_dir`=风险先验方向（研究先验，**未经真实结局校准**）。",
             ""]
    if failed:
        lines += [f"> ⚠ 以下维度本次出题失败、未计入：{'、'.join(failed)}", ""]
    n_q = 0
    n_good = 0
    n_bad = 0
    for dim in DIMENSIONS:
        qs = by_dim.get(dim["id"])
        if not qs:
            continue
        lines.append(f"## {dim['risk']} · {dim['id']}")
        lines.append(f"*倾向轴：{dim['axis']}　|　先验：{dim['prior']}*")
        lines.append("")
        for q in qs:
            n_q += 1
            val = q.get("价值", "?")
            n_good += val == "全好"
            n_bad += val == "全坏"
            lines.append(f"**Q{n_q}**（{val}·问\"{q.get('问法','')}\"）{q.get('情景','')}")
            for opt in q.get("选项", []):
                lines.append(
                    f"- {opt.get('id','')}. {opt.get('文本','')} "
                    f"`[{opt.get('dim_tendency','')}·{opt.get('risk_dir','')}]`")
            lines.append("")
    head = (f"> 本卷共 **{n_q}** 题（全好 {n_good} / 全坏 {n_bad}），"
            f"覆盖 {len([d for d in DIMENSIONS if by_dim.get(d['id'])])}/{len(DIMENSIONS)} 维。\n")
    lines.insert(4, head)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="AIG 测评卷出题器（JD→DeepSeek→情境迫选题）")
    ap.add_argument("--jd", default="JD158_新媒体运营经理", help="data/jd_samples 下的 JD 文件名或路径")
    ap.add_argument("--good", type=int, default=2, help="每维全好题数")
    ap.add_argument("--bad", type=int, default=1, help="每维全坏题数")
    ap.add_argument("--dims", default="", help="只出这些维度（逗号分隔维度名），缺省=全 8 维")
    args = ap.parse_args(argv)

    jd = load_jd(args.jd)
    dims = DIMENSIONS
    if args.dims:
        want = {x.strip() for x in args.dims.split(",")}
        dims = [d for d in DIMENSIONS if d["id"] in want]
    client = LLMClient("writer")

    by_dim: dict[str, list] = {}
    failed: list[str] = []
    for i, dim in enumerate(dims, 1):
        print(f"[{i}/{len(dims)}] 出题中：{dim['risk']}·{dim['id']} …", file=sys.stderr)
        try:
            qs = gen_dimension(client, jd, dim, args.good, args.bad)
            by_dim[dim["id"]] = qs
            print(f"    ✓ 得 {len(qs)} 题", file=sys.stderr)
        except LLMError as e:
            failed.append(dim["id"])
            print(f"    ✗ 失败：{e}", file=sys.stderr)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    outdir = OUTPUT_DIR / f"quiz_{jd.get('_jd_id','JD')}_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "卷.json").write_text(
        json.dumps({"jd": jd, "by_dim": by_dim, "failed": failed},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_md(jd, by_dim, failed)
    (outdir / "卷.md").write_text(md, encoding="utf-8")
    print(f"\n写出：{outdir}\\卷.md", file=sys.stderr)
    if failed:
        print(f"注意：{len(failed)} 个维度失败：{failed}", file=sys.stderr)
    # stdout 直接吐 md，方便管道/查看
    print(md)


if __name__ == "__main__":
    main()
