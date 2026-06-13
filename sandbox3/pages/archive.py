# sandbox3/pages/archive.py
"""把 run 目录的 trace.json 渲染成单文件自包含 HTML 档案页（file:// 直开，零外部依赖）。
搬自蓝本 relate_mvp/build_page.py（已验证资产），CSS/布局/承诺轨迹 SVG/诚实脚注整段保留；
名单制适配仅两处：①观察主体读 meta["candidate"]（蓝本读 m["newcomer"]）；
②beat 加换序三问表决行（照 trace.render 的表决明细句式）。
用法：python -m sandbox3.pages.archive [--run output/run_xxx]（缺省取最新 run）。"""
from __future__ import annotations
import argparse, html, json, pathlib

from ..config import OUTPUT_DIR
from ..states import STATE_ENUMS, STATE_LABELS


def _e(s) -> str:
    return html.escape(str(s if s is not None else ""))


CSS = """
:root{
  --paper:#f3eddd; --card:#fbf7ec; --ink:#2b2620; --muted:#8a7e6a;
  --line:#d9cfb6; --accent:#a3271d; --ok:#3f6e3f; --flag:#b07a10;
  --inner-bg:#2e2922; --inner-ink:#e9e0cc;
  --serif:"Noto Serif SC","Source Han Serif SC","SimSun","STSong",serif;
  --kai:"KaiTi","STKaiti","DFKai-SB",serif;
  --sans:"Microsoft YaHei","PingFang SC",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:var(--serif);line-height:1.85;
  background-image:radial-gradient(#0000 60%,#00000008 100%),
    repeating-linear-gradient(0deg,#0000 0 28px,#00000005 28px 29px)}
.wrap{max-width:900px;margin:0 auto;padding:48px 28px 96px}
header{border-bottom:3px double var(--line);padding-bottom:28px;margin-bottom:8px}
.kicker{font-family:var(--sans);font-size:12px;letter-spacing:.45em;color:var(--accent);
  text-transform:uppercase;margin-bottom:10px}
h1{font-size:34px;font-weight:900;letter-spacing:.06em}
h1 .sub{font-size:16px;font-weight:400;color:var(--muted);letter-spacing:.2em;margin-left:14px}
.meta{font-family:var(--sans);font-size:12px;color:var(--muted);margin-top:14px;display:flex;
  flex-wrap:wrap;gap:8px 22px}
.footnote{background:#f7e9c8;border:1px solid #dcbf7a;border-left:6px solid #b98a23;
  font-family:var(--sans);font-size:13px;line-height:1.7;padding:12px 16px;margin:22px 0 34px;color:#5d4a1d}
.traj{background:var(--card);border:1px solid var(--line);padding:22px 24px 14px;margin-bottom:44px}
.traj h2{font-family:var(--sans);font-size:13px;letter-spacing:.3em;color:var(--muted);margin-bottom:10px}
.traj svg{width:100%;height:130px;display:block}
.scene{position:relative;background:var(--card);border:1px solid var(--line);
  margin:0 0 52px 56px;padding:30px 34px 26px;box-shadow:6px 6px 0 #00000010}
.scene::before{content:attr(data-no);position:absolute;left:-66px;top:-18px;
  font-family:var(--sans);font-size:64px;font-weight:900;color:var(--accent);opacity:.85;line-height:1}
.cat{display:inline-block;font-family:var(--sans);font-size:11px;letter-spacing:.25em;
  color:#fff;background:var(--ink);padding:3px 12px;margin-bottom:6px}
h3{font-size:24px;font-weight:800;letter-spacing:.04em;margin-bottom:14px}
.block{margin:16px 0}
.lab{font-family:var(--sans);font-size:11px;letter-spacing:.3em;color:var(--accent);
  border-bottom:1px solid var(--line);padding-bottom:3px;margin-bottom:8px;display:block}
.setting{color:var(--muted);font-size:14px;font-family:var(--sans)}
.narr{font-size:15.5px;text-align:justify}
.beat{border:1px solid var(--line);border-left:5px solid var(--ink);margin:22px 0;
  padding:16px 20px;background:#fffdf6}
.beat-head{font-family:var(--sans);font-size:13px;font-weight:700;letter-spacing:.15em;
  margin-bottom:10px;display:flex;justify-content:space-between;align-items:center}
.beat-head .actor{color:var(--accent)}
.junc{border-left:4px solid var(--accent);background:#a3271d0d;padding:10px 16px;
  font-weight:700;margin:10px 0}
ul.opts{list-style:none}
ul.opts li{border:1px solid var(--line);background:#fff9;padding:10px 16px 10px 52px;margin:8px 0;
  position:relative;font-size:14.5px}
ul.opts li .oid{position:absolute;left:14px;top:9px;font-family:var(--sans);font-weight:900;
  color:var(--muted);font-size:16px}
ul.opts li .orig{font-family:var(--sans);font-size:10px;color:var(--muted);margin-left:6px}
ul.opts li.chosen{border:2px solid var(--accent);background:#fff}
ul.opts li.chosen::after{content:"选 定";position:absolute;right:12px;top:-12px;color:var(--accent);
  border:2px solid var(--accent);border-radius:4px;padding:2px 8px;font-family:var(--kai);
  font-size:14px;font-weight:700;letter-spacing:.2em;transform:rotate(6deg);background:#fff;
  box-shadow:1px 2px 0 #00000022}
.shuffle-note{font-family:var(--sans);font-size:11px;color:var(--muted)}
.votes{font-family:var(--sans);font-size:12px;color:#574e3f;background:#efe7d2;
  border:1px dashed #c4b58e;padding:8px 14px;margin:8px 0}
.votes b{color:var(--accent)}
.inner{background:var(--inner-bg);color:var(--inner-ink);padding:18px 22px;margin:14px 0;
  border-radius:2px;position:relative}
.inner .lab{color:#d8b15e;border-color:#ffffff22}
.inner .thought{font-family:var(--kai);font-size:17px;line-height:1.9}
.inner .seal{position:absolute;right:14px;top:12px;font-family:var(--kai);font-size:11px;
  color:#d8b15e;border:1px solid #d8b15e;padding:1px 6px;letter-spacing:.3em;opacity:.8}
.emos{display:flex;flex-wrap:wrap;gap:6px 18px;margin-bottom:10px}
.emo{font-family:var(--sans);font-size:12px;color:#bfb49a;display:flex;align-items:center;gap:6px}
.emo b{color:var(--inner-ink)}
.emo .bar{width:72px;height:5px;background:#ffffff1f;border-radius:3px;overflow:hidden}
.emo .bar i{display:block;height:100%;background:#d8b15e}
.reason{font-size:14.5px;color:#574e3f;background:#efe7d2;padding:12px 16px;border:1px dashed #c4b58e}
.reason .conf{font-family:var(--sans);font-size:12px;color:var(--muted)}
.audit{font-family:var(--sans);font-size:13px;padding:10px 14px;margin-top:10px;
  border:1px solid var(--line);background:#fff}
.audit .v{display:inline-block;font-weight:900;padding:1px 10px;border-radius:3px;
  margin-right:10px;letter-spacing:.2em}
.audit .v.ok{color:var(--ok);border:2px solid var(--ok)}
.audit .v.flag{color:#fff;background:var(--flag)}
.gap{font-family:var(--sans);font-size:12.5px;color:#8a6d1f;margin-top:8px}
table.states{width:100%;border-collapse:collapse;font-size:13px;font-family:var(--sans)}
table.states td{border-top:1px solid var(--line);padding:7px 10px;vertical-align:top}
table.states td.k{white-space:nowrap;color:var(--muted);width:110px}
table.states td.v{white-space:nowrap;width:150px}
.chg{color:var(--accent);font-weight:700}
.chip{display:inline-block;border:1px solid var(--line);background:#fff8;padding:0 8px;border-radius:3px}
.chg .chip{border-color:var(--accent)}
.relations{font-family:var(--sans);font-size:13px;margin-top:14px;background:#efe7d2;
  border:1px solid #c4b58e;padding:10px 14px}
.relations b{letter-spacing:.2em}
.commit{display:flex;align-items:baseline;gap:14px;border-top:3px double var(--line);
  margin-top:20px;padding-top:14px}
.commit .score{font-family:var(--sans);font-size:34px;font-weight:900;color:var(--accent)}
.commit .of{font-size:14px;color:var(--muted)}
.commit .why{font-size:13.5px;color:#574e3f}
.cons{font-family:var(--sans);font-size:13px;margin-top:12px;background:#efe7d2;
  border:1px solid #c4b58e;padding:10px 14px}
.cons b{letter-spacing:.2em}
.next{font-family:var(--sans);font-size:12.5px;color:var(--muted);margin-top:14px;
  border-left:3px solid var(--line);padding-left:12px}
.warn{font-family:var(--sans);font-size:12.5px;color:#8a4a12;background:#f3dfc2;
  padding:8px 12px;margin-top:12px}
footer{font-family:var(--sans);font-size:12px;color:var(--muted);border-top:1px solid var(--line);
  padding-top:18px;text-align:center;letter-spacing:.15em}
"""


def _traj_svg(points: list[tuple[int, float | None]]) -> str:
    W, H, PADX, PADY = 820, 130, 46, 18
    xs = lambda i: PADX + i * (W - 2 * PADX) / max(1, len(points) - 1)
    ys = lambda v: H - PADY - (v / 5.0) * (H - 2 * PADY)
    grid = "".join(
        f'<line x1="{PADX}" y1="{ys(v)}" x2="{W - PADX}" y2="{ys(v)}" stroke="#d9cfb6" stroke-width="0.6"/>'
        f'<text x="{PADX - 10}" y="{ys(v) + 4}" font-size="10" fill="#8a7e6a" text-anchor="end">{v}</text>'
        for v in range(6))
    poly = " ".join(f"{xs(i)},{ys(c)}" for i, (_, c) in enumerate(points) if c is not None)
    dots = "".join(
        f'<circle cx="{xs(i)}" cy="{ys(c)}" r="5" fill="#a3271d"/>'
        f'<text x="{xs(i)}" y="{ys(c) - 12}" font-size="13" font-weight="700" fill="#2b2620" text-anchor="middle">{c}</text>'
        f'<text x="{xs(i)}" y="{H - 2}" font-size="11" fill="#8a7e6a" text-anchor="middle">第{n}幕</text>'
        for i, (n, c) in enumerate(points) if c is not None)
    return (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">{grid}'
            f'<polyline points="{poly}" fill="none" stroke="#a3271d" stroke-width="2.5"/>{dots}</svg>')


def _votes_html(bt: dict) -> str:
    # 名单制适配②：换序三问表决行（照 trace.render 的表决明细句式）
    vs = bt.get("vote_summary")
    if not vs:
        return ""
    seq = " · ".join(f"第{v['round']}问→原{v['orig_id']}（呈现位{v['position']}）"
                     for v in bt.get("votes") or [])
    return (f'<div class="votes">🗳 <b>换序三问表决</b>（防位置偏置）：{_e(seq)} '
            f'⇒ {_e(vs["verdict"])}，取原{_e(vs["winner_orig_id"])}</div>')


def _beat_html(bt: dict) -> str:
    dec, appr, audit = bt["decision"], bt.get("appraisal", {}), bt.get("audit", {})
    opts = "".join(
        f'<li class="{"chosen" if o["id"] == dec.get("action_id") else ""}">'
        f'<span class="oid">{_e(o["id"])}</span>{_e(o["text"])}'
        f'<span class="orig">原序 {_e(o.get("orig_id", "?"))}</span></li>'
        for o in bt["options"])
    emos = "".join(
        f'<span class="emo">{_e(k)} <span class="bar"><i style="width:{int(v)}%"></i></span> <b>{int(v)}</b></span>'
        for k, v in appr.get("emotions", {}).items() if isinstance(v, (int, float)))
    tags = "、".join(dec.get("emotion_tags") or [])
    fab = audit.get("fabricated_cues") or []
    ok = audit.get("verdict") == "通过"
    gap = audit.get("inner_gap") or "无"
    gap_html = (f'<div class="gap">心口缝（只记录不打分）：{_e(gap)}</div>'
                if gap not in ("无", "") else "")
    return f"""
  <div class="beat">
    <div class="beat-head"><span>回 合 {bt['beat']}　<span class="actor">行动方 — {_e(bt['acting_agent'])}</span></span></div>
    <div class="narr">{_e(bt['narration'])}</div>
    <div class="junc">{_e(bt['juncture'])}</div>
    <span class="lab">候 选 行 动 <span class="shuffle-note">（呈现顺序已随机打乱，防位置偏置）</span></span>
    <ul class="opts">{opts}</ul>
    {_votes_html(bt)}
    <div class="inner"><span class="seal">内 心 密 档</span><span class="lab">{_e(bt['acting_agent'])} 的内心</span>
      <div class="emos">{emos}</div>
      <div class="thought">{_e(appr.get('internal_thoughts', '（无）'))}</div></div>
    <div class="reason">{_e(dec.get('reasoning', ''))}<br>
      <span class="conf">信心 {_e(dec.get('confidence', '?'))} ／ 情绪标签：{_e(tags)}</span></div>
    <div class="audit"><span class="v {'ok' if ok else 'flag'}">{_e(audit.get('verdict', '?'))}</span>
      手册命中：{_e('、'.join(audit.get('playbook_match') or []) or '无')}　|
      手册冲突：{_e(audit.get('playbook_conflict', '无'))}　|
      与内心：{_e(audit.get('thought_consistency', '?'))}（{_e(audit.get('thought_note', ''))}）　|
      编造线索：{_e('、'.join(fab) if fab else '无')}　|
      信息越权：{_e(audit.get('info_overreach') or '无')}<br>{_e(audit.get('note', ''))}</div>
    {gap_html}
  </div>"""


def _scene_html(sc: dict) -> str:
    tp, scene = sc["turning_point"], sc["scene"]
    beats = "".join(_beat_html(bt) for bt in sc["beats"])
    rows = []
    for k in STATE_ENUMS:
        v, ev = sc["states"].get(k, "?"), sc.get("evidence", {}).get(k, "")
        if k in sc.get("state_changes", {}):
            a, b = sc["state_changes"][k]
            cell = f'<span class="chg"><span class="chip">{_e(a)}</span> → <span class="chip">{_e(b)}</span></span>'
        else:
            cell = f'<span class="chip">{_e(v)}</span>'
        rows.append(f'<tr><td class="k">{_e(STATE_LABELS[k])}</td><td class="v">{cell}</td><td>{_e(ev)}</td></tr>')
    rels = sc.get("relations") or {}
    rels_html = (('<div class="relations"><b>关 系 细 目（候选人×成员，只入档不进灯）</b><br>' +
                  "<br>".join(f"· {_e(nm)}：{_e(r.get('attitude', '?'))}——{_e(r.get('evidence', ''))}"
                             for nm, r in rels.items()) + "</div>")
                 if rels else "")
    cons = sc.get("consequences") or []
    cons_html = (('<div class="cons"><b>后 果 结 算（入台账）</b><br>' +
                  "<br>".join(f"· {_e(c['matter'])} → {_e(c['outcome'])}" for c in cons) + "</div>")
                 if cons else "")
    nxt = sc.get("next_tp")
    nxt_html = (f'<div class="next">下一幕：状态灯触发类别 {_e("、".join(nxt["heuristic_categories"]))} → '
                f'选 <b>{_e(nxt["choice"])}</b>（{_e(nxt["why"])}）</div>') if nxt else ""
    warn_html = (f'<div class="warn">⚠ {_e("；".join(sc["warnings"]))}</div>') if sc.get("warnings") else ""
    return f"""
<section class="scene" data-no="{sc['index']:02d}">
  <span class="cat">{_e(tp['category'])}</span>
  <h3>{_e(tp['title'])}</h3>
  <div class="block setting">{_e(scene.get('setting', ''))}</div>
  <div class="block narr">{_e(scene.get('current_scene', ''))}</div>
  {beats}
  <div class="block"><span class="lab">状 态 灯</span>
    <table class="states">{''.join(rows)}</table></div>
  {rels_html}
  <div class="commit"><span class="score">{_e(sc.get('commitment'))}</span><span class="of">/ 5 留任-契合承诺</span>
    <span class="why">{_e(sc.get('commitment_rationale', ''))}</span></div>
  {cons_html}{nxt_html}{warn_html}
</section>"""


def build(run_dir: pathlib.Path) -> pathlib.Path:
    trace = json.loads((run_dir / "trace.json").read_text(encoding="utf-8"))
    m = trace["meta"]
    points = [(sc["index"], sc.get("commitment")) for sc in trace["scenes"]]
    scenes = "".join(_scene_html(sc) for sc in trace["scenes"])
    actors = "、".join(f"{_e(k)} {v} 次" for k, v in m.get("actor_counts", {}).items())
    # 名单制适配①：观察主体读 meta["candidate"]；在场名单读 meta["cast"]
    cand = m.get("candidate", "?")
    cast_s = "、".join(f"{_e(c['name'])}（{_e(c.get('kind', '?'))}）" for c in m.get("cast") or []) or "—"
    page = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPOILER · 受控选项推演 — {_e(run_dir.name)}</title><style>{CSS}</style></head>
<body><div class="wrap">
<header>
  <div class="kicker">SPOILER · Controlled-Option Rollout</div>
  <h1>人事观察档案<span class="sub">SPOILER · 受控选项推演 MVP（名单制）</span></h1>
  <div class="meta"><span>观察主体：{_e(cand)}（候选人）</span>
    <span>在场名单：{cast_s}</span>
    <span>模型：{_e(m['model'])}</span><span>幕数：{m['n_scenes']}</span>
    <span>LLM 调用：{m['n_llm_calls']} 次</span><span>用时：{_e(m.get('elapsed_s', '?'))}s</span>
    <span>行动方分布：{actors}</span><span>审计黄旗：{m.get('audit_flags', 0)} 个</span>
    <span>警告：{m['warnings_total']} 条</span><span>{_e(run_dir.name)}</span></div>
</header>
<div class="footnote">⚠ 诚实脚注：本页为<b>单 run 轨迹</b>（论文原设计为 5 run 聚合）；人设为手写合成（可为蒸馏产物）；
"留任-契合承诺"是推演机制的内部部件、<b>未经任何对账校准，不构成对真实结局的预测</b>；
状态灯只依据可观察行为推断，内心密档不进入状态评估；关系细目只入档不进灯；
理由审计员同为 AI，做的是<b>结构对账</b>（条款命中/内心自洽/线索查证），非语义终审，黄旗供人复核；
名单制多人：同事亦为真 agent。</div>
<div class="traj"><h2>承 诺 轨 迹</h2>{_traj_svg(points)}</div>
{scenes}
<footer>SPOILER — sandbox3 ／ 架构参照 RELATE-Sim（arXiv 2510.00414）／ 本页由 trace.json 生成</footer>
</div></body></html>"""
    out = run_dir / "档案.html"
    out.write_text(page, encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None, help="run 目录（缺省取最新）")
    args = ap.parse_args()
    run_dir = pathlib.Path(args.run) if args.run else sorted(OUTPUT_DIR.glob("run_*"))[-1]
    out = build(run_dir)
    print(f"已生成：{out}")


if __name__ == "__main__":
    main()
