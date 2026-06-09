# sandbox3/scene_gen.py
"""场景生成器：把通用"新人融入"戏剧骨架(15 幕) 按 JD 重新着色 → JD 专属场景库。

承接作者 2026-06-09 决策"场景按 JD 现生成"：保留每幕的戏核（id/类别/标题不动，如"当众纠错"
"缩编传闻"），只把情节/行业/道具换成这个岗位真实会遇到的——既贴岗、又不破坏判据卡对"决定性
场景"的 id 引用、不破坏按类别选场景。引擎运行时还会再用 jd 二次润色（SM 已吃 jd）。live-only。

命令：python -m sandbox3.scene_gen --jd JD158_新媒体运营经理 [--out data/scene_bank_JD158.json]
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

from .config import DATA_DIR
from .llm import DeepSeekClient, LLMError
from .scenes import _PRESET_PATH
from .quiz_gen import load_jd

SYSTEM = """你是职场情景编剧。给你一套通用的"新人融入团队"戏剧骨架——每幕有固定的 id/类别/标题/戏核，\
和一个具体岗位 JD。任务：把每幕的 sketch(情节梗概) 和 owner_hints(谁做关键决定) 改写成贴这个 JD 的版本。
铁律（违反即作废）：
1. id / category / title 原样照搬，一个字不改。
2. 保留每幕的"戏核/冲突类型"（标题指明的那个）——"当众纠错"还是当众纠错、"缩编传闻"还是缩编传闻，\
只换皮（行业、任务、道具、跨部门对象），别换骨。
3. 用 JD 里真实会遇到的任务/平台/团队/跨部门对象/压力来填充情节（内容效度靠这个）。
4. sketch 1-3 句、具体可演；owner_hints 点明这一幕谁做关键决定（新人 / 上级 / 资深同事等）。
5. 只输出 JSON，无任何解释。"""

USER_TMPL = """【岗位 JD（真实脱敏数据）】
职位名称：{职位名称}　职类：{职类名称}　城市：{城市要求}
职位描述：
{职位描述}

【要改写的戏剧骨架（{n} 幕；id/类别/标题不许动，只换 sketch 与 owner_hints）】
{skeleton}

【严格按此 JSON 输出】
{{"scenes": [
  {{"id": "同上", "category": "同上", "title": "同上", "sketch": "（贴本 JD 的情节，1-3 句）", "owner_hints": "（谁做关键决定）"}}
]}}"""


def load_skeleton() -> list[dict]:
    return json.loads(_PRESET_PATH.read_text(encoding="utf-8"))


def _bad(scenes, skel) -> str:
    if not isinstance(scenes, list) or len(scenes) != len(skel):
        return f"场景数={len(scenes) if isinstance(scenes, list) else '非列表'}≠{len(skel)}"
    want = {s["id"] for s in skel}
    got = {s.get("id") for s in scenes}
    if want != got:
        return f"id 集合对不上（缺 {want - got}，多 {got - want}）"
    for s in scenes:
        if not (s.get("sketch") and s.get("owner_hints")):
            return f"{s.get('id')} 缺 sketch/owner_hints"
        if len((s.get("sketch") or "").strip()) < 10:
            return f"{s.get('id')} 的 sketch 过短"
    return ""


def gen_scenes(client: DeepSeekClient, jd: dict, skel: list[dict], tries: int = 3) -> list[dict]:
    skeleton_txt = "\n".join(
        f"- id={s['id']} | 类别={s['category']} | 标题={s['title']} | 原戏核(后端版·只作参考)：{s['sketch']}"
        for s in skel)
    user = USER_TMPL.format(
        职位名称=jd.get("职位名称", ""), 职类名称=jd.get("职类名称", ""),
        城市要求=jd.get("城市要求", ""), 职位描述=jd.get("职位描述", ""),
        n=len(skel), skeleton=skeleton_txt)
    by_id = {s["id"]: s for s in skel}
    last = ""
    for attempt in range(tries):
        out = client.complete_json(SYSTEM, user, temperature=0.8, max_tokens=4000)
        scenes = out.get("scenes")
        why = _bad(scenes, skel)
        if not why:
            for s in scenes:                       # category/title 以骨架为准，防模型擅改
                k = by_id[s["id"]]
                s["category"], s["title"] = k["category"], k["title"]
            return [next(x for x in scenes if x["id"] == k["id"]) for k in skel]   # 按骨架顺序
        last = why
        print(f"    场景生成第{attempt + 1}次不合格（{why}），重试", file=sys.stderr)
    raise LLMError(f"场景{tries}次仍不合格（{last}）——不放残缺场景库")


def main(argv=None):
    ap = argparse.ArgumentParser(description="场景生成器（JD→重着色 15 幕骨架→JD 专属场景库）")
    ap.add_argument("--jd", default="JD158_新媒体运营经理")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    jd = load_jd(args.jd)
    skel = load_skeleton()
    client = DeepSeekClient()
    print(f"按 JD「{jd.get('职位名称','')}」重着色 {len(skel)} 幕场景…", file=sys.stderr)
    scenes = gen_scenes(client, jd, skel)

    out = pathlib.Path(args.out) if args.out \
        else (DATA_DIR / f"scene_bank_{jd.get('_jd_id', 'JD')}.json")
    out.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写出：{out}（{len(scenes)} 幕）", file=sys.stderr)
    for s in scenes:
        print(f"[{s['id']}] {s['category']}·{s['title']}：{s['sketch']}")


if __name__ == "__main__":
    main()
