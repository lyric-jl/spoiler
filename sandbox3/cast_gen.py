# sandbox3/cast_gen.py
"""团队 cast 生成器：JD → DeepSeek 现搭"代表性团队"（直属上级 + 同事原型）。

承接作者 2026-06-09 决策"团队纯 JD 现搭原型"：候选人来自测评卷画像（另一条路、不在此），
团队同事不答测评卷——按 JD 的真实团队语境（带谁、跟谁跨部门、向谁汇报、典型冲突）现生成
角色原型。诚实口径（随产物走）：这是"代表性团队 / 原型"，性格为可信虚构、非真人；
真实部署可换成公司自有员工数据（他评 / 绩效 / 360）。live-only，走编剧模型（config.ROLES writer），
失败大声抛 / 标，绝不用空卡冒充。

输出可直接喂沙盘：python -m sandbox3.run --cast output/team_xxx/cast_runnable.json
命令：python -m sandbox3.cast_gen [--jd JD158_新媒体运营经理] [--others 3] [--candidate <cast.json>]
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys
import time

from .config import DATA_DIR, OUTPUT_DIR, MAX_CAST
from .cast import Cast, CastError
from .llm import LLMClient, LLMError
from .quiz_gen import load_jd  # 复用 JD 加载（带或不带 .json / 完整路径）

# ---- 金标卡（few-shot）：默认名单里的"沈雯"，锚住人设/手册的"活人感"与写法 ----
GOLDEN = """姓名：沈雯（34 岁）
角色：直属上级·后端组组长（带 6 人，新人的汇报对象）
人设：你是沈雯，34 岁，后端组组长，带 6 个人。你节奏快、务实，最看重'交付可预期'：\
宁可下属早早暴露问题，也不要憋到最后给你惊喜。你对模糊容忍度低，开会问'有没有问题'是真的在问。\
你欣赏主动汇报的人，对闷头干的人会先观望，但观望期不超过几周——带不动的人你会把核心活收回来给老人做，\
在你看来是对项目负责、不是针对谁。你其实惜才，会在评审会上替有真本事的新人挡刀，但你不哄人、反馈直接。\
最近上面在收紧编制，你的组明年可能要和另一个后端组合并，这件事你没跟下面的人说。
行为手册：
1. 如果新人按时交付且质量过关 → 给更有分量的活，开始在会上让他露脸。
2. 如果新人闷头不汇报 → 先观望两周，然后直接点名要日报/周报。
3. 如果交付出了问题 → 当众就事论事指出来，但散会后不再翻旧账。
4. 如果下属当面提出有数据支撑的反对意见 → 认真听，被说服就改，并记住这个人。
5. 如果上面压下来紧急任务 → 优先派给最稳的人；新人只给打下手的活。"""

SYSTEM = """你是资深组织行为顾问 + 职场编剧。给定一家公司某个真实岗位的 JD，\
你要为"即将入职这个岗位的新人"搭出他入职后朝夕相处的【代表性团队】——直属上级 + 几位关键同事/跨部门对接人。\
这套团队用于职场沙盘推演：看新人和这些人怎么磨合、起冲突、累积关系。

铁律（违反即作废）：
1. 团队必须长在这份 JD 的真实语境上：用 JD 写到的团队规模、要带的人、汇报关系、跨部门对象、\
典型任务与冲突/压力，来决定有哪些角色。别搭放之四海皆准的空泛角色（如泛泛的"一个同事"）。
2. 角色构成：有且仅有 1 个 kind="counterpart"=新人的直属上级（汇报对象）；其余都是 kind="colleague"\
（同组同事、资深老人、跨部门对接人等）。一共 {n_others} 个人（不含新人自己）。
3. 每个人要像活人、彼此有区分度：各自的性格、做事风格、在乎什么、会因为什么和新人或别人起摩擦。\
最好每人藏一个不主动外露的小算盘或软肋（像真团队那样），用来制造磨合张力——\
但别写成脸谱化的纯反派，也别全是老好人。
4. persona 用第二人称"你是X……"写，150-250 字，须包含：姓名/年龄/在团队的角色；性格与做事风格；\
在乎或忌讳什么；和新人会怎样产生摩擦；一个藏起来、不主动外露的点。
5. playbook=3-7 条"如果……就……"行为手册，具体、可触发、像真人的条件反射，别写贴标签的空话。
6. 名字别和新人重名，几个人互相也别重名。只输出 JSON，不要任何解释性文字。"""

USER_TMPL = """【岗位 JD（真实脱敏数据）】
职位名称：{职位名称}
职类：{职类名称}　薪资：{薪资}　年限：{年限要求}　学历：{学历要求}　城市：{城市要求}
职位关键词：{职位关键词}
职位描述：
{职位描述}

【新人是谁】一位刚入职这个岗位、处于试用期的新人——他的具体画像来自测评卷（你不用编新人，\
只搭他周围的团队）。请从 JD 读出：他向谁汇报、要带哪些人、跟哪些部门打交道、这个岗位最容易和谁起冲突。

【要搭的团队】共 {n_others} 人：1 个直属上级(counterpart) + {n_colleague} 个同事/跨部门对接人(colleague)。

【质量样板（这是另一个岗位的金标准，照这个"活人感"与写法，但角色和情节要全换成贴本 JD 的）】
{golden}

【严格按此 JSON 输出】（role/persona/playbook 都要贴本 JD，别照抄样板）
{{
  "team": [
    {{"name": "（中文名）", "kind": "counterpart",
      "role": "直属上级·（贴 JD 的具体头衔 + 一句职责）",
      "persona": "你是……（150-250字，第二人称）",
      "playbook": ["如果……就……", "如果……就……", "如果……就……"]}},
    {{"name": "（中文名）", "kind": "colleague",
      "role": "（贴 JD 的角色，如 内容团队资深策划 / 设计部对接人）",
      "persona": "你是……",
      "playbook": ["如果……就……", "如果……就……", "如果……就……"]}}
  ]
}}"""


def load_candidate(path: pathlib.Path) -> dict:
    """从一份 cast JSON 里取出 candidate 卡（沙盘要求恰好 1 个 candidate）。"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    cands = [c for c in raw if c.get("kind") == "candidate"]
    if not cands:
        raise SystemExit(f"{path} 里没有 candidate 卡")
    return cands[0]


def _bad_team(team, n_others: int, cand_name: str) -> str:
    """返回不合格原因（空串=合格）。结构闸：人数、恰好 1 个上级、字段齐、手册 3-9 条、人设够长、不重名。"""
    if not isinstance(team, list) or len(team) != n_others:
        return f"团队人数={len(team) if isinstance(team, list) else '非列表'}≠{n_others}"
    cps = [t for t in team if t.get("kind") == "counterpart"]
    if len(cps) != 1:
        return f"counterpart(直属上级)需恰好 1 个，得到 {len(cps)}"
    seen = set()
    for i, t in enumerate(team, 1):
        for k in ("name", "kind", "role", "persona", "playbook"):
            if not t.get(k):
                return f"第{i}人缺字段 {k}"
        if t["kind"] not in ("counterpart", "colleague"):
            return f"第{i}人 kind 越界：{t['kind']!r}"
        pb = t["playbook"]
        if not isinstance(pb, list) or not 3 <= len(pb) <= 9:
            return f"{t['name']} 的 playbook 需 3-9 条列表"
        if len((t.get("persona") or "").strip()) < 60:
            return f"{t['name']} 的 persona 过短（<60字）"
        if t["name"] == cand_name:
            return f"{t['name']} 与候选人重名"
        if t["name"] in seen:
            return f"人名重复：{t['name']}"
        seen.add(t["name"])
    return ""


def gen_team(client: DeepSeekClient, jd: dict, n_others: int,
             cand: dict, tries: int = 3) -> list[dict]:
    user = USER_TMPL.format(
        职位名称=jd.get("职位名称", ""), 职类名称=jd.get("职类名称", ""),
        薪资=jd.get("薪资", ""), 年限要求=jd.get("年限要求", ""),
        学历要求=jd.get("学历要求", ""), 城市要求=jd.get("城市要求", ""),
        职位关键词=jd.get("职位关键词", ""), 职位描述=jd.get("职位描述", ""),
        n_others=n_others, n_colleague=n_others - 1, golden=GOLDEN,
    )
    last = ""
    for attempt in range(tries):
        out = client.complete_json(SYSTEM, user, temperature=0.9, max_tokens=4000)
        team = out.get("team")
        why = _bad_team(team, n_others, cand["name"])
        if not why:
            # 终极闸：拼上候选人，过一遍沙盘真正的 Cast 校验（重名/candidate 唯一性等）
            try:
                Cast.from_cards([cand] + team)
                return team
            except CastError as e:
                why = f"Cast 校验未过：{e}"
        last = why
        print(f"    团队第{attempt + 1}次不合格（{why}），重试", file=sys.stderr)
    raise LLMError(f"团队{tries}次仍生成不合格（{last}）——不放空卡混过")


def render_md(jd: dict, cand: dict, team: list[dict]) -> str:
    jd_id = jd.get("_jd_id", "JD")
    L = [f"# 现搭代表性团队 · {jd.get('职位名称','')}",
         "",
         f"> 出题源 JD：**{jd_id}** {jd.get('职位名称','')}"
         f"（{jd.get('职类名称','')}／{jd.get('城市要求','')}／{jd.get('薪资','')}）——{jd.get('_源','真实脱敏数据')}",
         "> 谁搭的：**DeepSeek-chat（产品自家栈）**。这是按 JD 现搭的【代表性团队 / 原型】——"
         "性格为可信虚构、非真人；真实部署可换成公司自有员工数据（他评 / 绩效 / 360）。",
         f"> 候选人：本文件用占位候选人「**{cand.get('name','?')}**」凑数以便跑通沙盘；"
         "真实候选人来自测评卷画像，与此团队配对。",
         "> ⚠ 当前沙盘场景库(scene_bank)措辞按后端岗写，跑本岗团队会语境串味——要完全连贯，"
         "场景也需按 JD 本地化（下一步）。",
         ""]
    label = {"counterpart": "直属上级", "colleague": "同事"}
    for t in team:
        L.append(f"## {label.get(t['kind'], t['kind'])}（{t['kind']}）· {t['role']}")
        L.append(t["persona"])
        L.append("")
        L.append("**行为手册（如果…就…）**")
        L += [f"{i}. {r}" for i, r in enumerate(t["playbook"], 1)]
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="团队 cast 生成器（JD→DeepSeek→代表性团队原型）")
    ap.add_argument("--jd", default="JD158_新媒体运营经理", help="data/jd_samples 下的 JD 文件名或路径")
    ap.add_argument("--others", type=int, default=3, help="团队人数（不含候选人）：1 上级 + 余下同事")
    ap.add_argument("--candidate", default=None,
                    help="从哪份 cast JSON 取占位候选人（缺省=data/cast_default.json 的周默）")
    args = ap.parse_args(argv)

    if not 2 <= args.others <= MAX_CAST - 1:
        raise SystemExit(f"--others 需在 2~{MAX_CAST - 1}（含 1 上级 + ≥1 同事，且总人数≤{MAX_CAST}）")

    jd = load_jd(args.jd)
    jd_id = jd.get("_jd_id", "JD")
    cand = load_candidate(pathlib.Path(args.candidate) if args.candidate
                          else DATA_DIR / "cast_default.json")

    client = LLMClient("writer")
    print(f"按 JD「{jd.get('职位名称','')}」现搭 {args.others} 人团队"
          f"（1 上级 + {args.others - 1} 同事）…", file=sys.stderr)
    team = gen_team(client, jd, args.others, cand)
    for t in team:                       # 诚实标注出身，随卡走（Cast 只读 5 字段、额外键忽略）
        t["_source"] = f"jd-archetype@{jd_id}"

    cast_list = [cand] + team
    Cast.from_cards(cast_list)           # 收尾再断言一次：可直接喂沙盘

    stamp = time.strftime("%Y%m%d-%H%M%S")
    outdir = OUTPUT_DIR / f"team_{jd_id}_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "cast_runnable.json").write_text(
        json.dumps(cast_list, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render_md(jd, cand, team)
    (outdir / "团队.md").write_text(md, encoding="utf-8")
    print(f"\n写出：{outdir}\\团队.md（+ cast_runnable.json 可 --cast 喂沙盘）", file=sys.stderr)
    print(md)


if __name__ == "__main__":
    main()
