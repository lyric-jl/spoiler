# sandbox3/pages/replay.py
"""放映厅：把 trace.json 渲染成可交互回放的单文件 HTML（file:// 直开，零外部依赖）。
搬自蓝本 relate_mvp/build_theater.py（已验证资产），CSS/布局/字幕卡/结算卡/连线/
心理默认隐藏（点头像才展开、展开即暂停）/诚实脚注整段保留；名单制适配仅三处：
①cast/candidate 从 meta 注入 JS（蓝本硬编码 ['周默','沈雯']）；演员列由 CAST 数组驱动，
候选人居左、其余真 agent 按 kind 排列、场景 npc 灰头像缀尾；
②收场卡加 relations 关系细目；③beat 加换序三问表决行（照 trace.render 句式）。
用法：python -m sandbox3.pages.replay [--run output/run_xxx]（缺省取最新）。"""
from __future__ import annotations
import argparse, json, pathlib

from ..config import OUTPUT_DIR

CSS = """
:root{
  --paper:#f3eddd; --card:#fbf7ec; --ink:#2b2620; --muted:#8a7e6a;
  --line:#d9cfb6; --accent:#a3271d; --gold:#d8b15e;
  --stage:#26211b; --stage2:#322c24; --stage-ink:#e9e0cc;
  --ok:#3f6e3f; --flag:#b07a10;
  --serif:"Noto Serif SC","Source Han Serif SC","SimSun","STSong",serif;
  --kai:"KaiTi","STKaiti","DFKai-SB",serif;
  --sans:"Microsoft YaHei","PingFang SC",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);overflow:hidden}
.app{display:grid;grid-template-columns:300px 1fr;height:100vh}

/* ---- 左：控制台 ---- */
.console{background:var(--card);border-right:2px solid var(--line);display:flex;
  flex-direction:column;overflow:hidden}
.console h1{font-family:var(--serif);font-size:19px;font-weight:900;letter-spacing:.08em;
  padding:18px 18px 4px}
.console .sub{font-size:11px;color:var(--muted);padding:0 18px 10px;letter-spacing:.15em}
.console .meta{font-size:11px;color:var(--muted);padding:0 18px 12px;line-height:1.8;
  border-bottom:1px solid var(--line)}
.ctrl{display:flex;gap:8px;padding:12px 18px;border-bottom:1px solid var(--line)}
.ctrl button{flex:1;font-family:var(--sans);font-size:13px;padding:8px 0;cursor:pointer;
  background:var(--ink);color:#fff;border:none;border-radius:3px;letter-spacing:.1em}
.ctrl button:hover{background:var(--accent)}
.ctrl button.playing{background:var(--accent)}
.toc{flex:1;overflow-y:auto;padding:10px 0}
.toc .scene-h{font-size:12px;font-weight:700;padding:8px 18px 4px;color:var(--accent);
  letter-spacing:.1em;cursor:pointer}
.toc .step{font-size:12px;padding:5px 18px 5px 30px;cursor:pointer;color:#574e3f;
  border-left:3px solid transparent}
.toc .step:hover{background:#00000008}
.toc .step.active{border-left-color:var(--accent);background:#a3271d12;font-weight:700}
.foot{font-size:10.5px;color:#5d4a1d;background:#f7e9c8;border-top:1px solid #dcbf7a;
  padding:10px 14px;line-height:1.7}

/* ---- 右：放映厅 + 审核 ---- */
.main{display:grid;grid-template-rows:minmax(0,58%) minmax(0,42%);overflow:hidden}
.stage-wrap{position:relative;background:var(--stage);overflow:hidden;
  border-bottom:4px double var(--gold)}
.stage-head{position:absolute;top:0;left:0;right:0;display:flex;justify-content:space-between;
  padding:10px 16px;font-size:11px;color:#bfb49a;letter-spacing:.2em;z-index:5}
.stage{position:relative;height:100%;display:flex;flex-direction:column;padding:40px 24px 14px}

/* 字幕卡 */
.titlecard{position:absolute;inset:0;background:#16120d;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:20;color:var(--stage-ink);text-align:center;
  padding:0 60px}
.titlecard .no{font-family:var(--sans);font-size:13px;letter-spacing:.5em;color:var(--gold);
  margin-bottom:14px}
.titlecard h2{font-family:var(--serif);font-size:30px;font-weight:900;letter-spacing:.1em;
  margin-bottom:16px}
.titlecard p{font-family:var(--serif);font-size:14px;color:#bfb49a;line-height:1.9;max-width:620px}

/* 结算卡 */
.settlecard{position:absolute;inset:0;background:#16120dee;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:20;color:var(--stage-ink);padding:0 70px}
.settlecard .tag{font-size:12px;letter-spacing:.4em;color:var(--gold);margin-bottom:12px}
.settlecard p{font-family:var(--serif);font-size:15px;line-height:2;max-width:640px}
.settlecard .cons{margin-top:14px;font-size:12.5px;color:#bfb49a;max-width:640px;line-height:1.9}
.settlecard .rels{margin-top:12px;font-size:12.5px;color:#cfc4ab;max-width:640px;line-height:1.9}
.settlecard .rels b{color:var(--gold)}

/* 舞台主体 */
.narr-strip{font-family:var(--serif);font-size:13.5px;color:#cfc4ab;line-height:1.8;
  max-height:96px;overflow-y:auto;padding:4px 10px;border-left:3px solid #4a4032;margin-bottom:8px}
.junc-strip{font-family:var(--serif);font-size:13.5px;color:#fff;background:#a3271d33;
  border-left:3px solid var(--accent);padding:6px 10px;margin-bottom:12px}
.floor{flex:1;display:flex;gap:18px;min-height:0;position:relative}
.cast{display:flex;flex-direction:column;justify-content:center;gap:18px;width:188px;
  flex-shrink:0;z-index:3}
.actor{display:flex;flex-direction:column;align-items:center;position:relative}
.ava{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-family:var(--kai);font-size:26px;font-weight:700;color:#fff;border:3px solid #4a4032;
  position:relative;transition:box-shadow .4s,border-color .4s}
.actor.acting .ava{border-color:var(--gold);box-shadow:0 0 18px #d8b15e88}
.actor .nm{font-size:12px;color:var(--stage-ink);margin-top:6px;letter-spacing:.1em}
.actor .rl{font-size:10px;color:#8a7e6a}
.actor.npc .ava{width:44px;height:44px;font-size:18px;background:#4a4338;border-color:#3a342b}
.actor.npc .nm{color:#9a8f7a}
.innertab{margin-top:6px;font-size:10.5px;color:var(--gold);border:1px solid #d8b15e55;
  border-radius:3px;padding:1px 10px;cursor:pointer;letter-spacing:.2em;background:#0000}
.innertab:hover{background:#d8b15e22}
.innertab.disabled{color:#6a614f;border-color:#4a4032;cursor:not-allowed}
.innerpanel{display:none;position:absolute;left:100%;top:0;margin-left:12px;width:300px;
  background:var(--stage2);border:1px solid var(--gold);padding:12px 14px;z-index:30;
  box-shadow:0 6px 24px #000a}
.innerpanel.open{display:block}
.innerpanel .ttl{font-size:11px;color:var(--gold);letter-spacing:.3em;margin-bottom:8px}
.innerpanel .thought{font-family:var(--kai);font-size:14.5px;color:var(--stage-ink);line-height:1.9}
.innerpanel .emo{display:flex;align-items:center;gap:6px;font-size:11px;color:#bfb49a;margin:3px 0}
.innerpanel .bar{flex:1;height:5px;background:#ffffff1f;border-radius:3px;overflow:hidden}
.innerpanel .bar i{display:block;height:100%;background:var(--gold)}
.innerpanel .none{font-size:12px;color:#8a7e6a;line-height:1.7}

/* 选项矩形框 */
.optbox{flex:1;border:2px solid #d8b15e66;background:#ffffff08;padding:14px 16px;
  align-self:center;max-width:560px;min-width:0;z-index:3}
.optbox .ttl{font-size:11px;color:var(--gold);letter-spacing:.3em;margin-bottom:10px}
.opt{border:1px solid #ffffff2a;background:#ffffff0a;padding:8px 12px 8px 38px;margin:7px 0;
  font-family:var(--serif);font-size:13px;color:var(--stage-ink);position:relative;
  line-height:1.7;transition:border-color .4s,background .4s}
.opt .oid{position:absolute;left:11px;top:7px;font-family:var(--sans);font-weight:900;
  color:#8a7e6a;font-size:13px}
.opt .orig{font-size:9.5px;color:#6a614f;margin-left:6px}
.opt .vts{color:var(--gold);font-size:10px;margin-left:8px;letter-spacing:2px}
.opt.chosen{border-color:var(--gold);background:#d8b15e1c}
.opt.chosen .oid{color:var(--gold)}
.votestrip{font-size:11px;color:#cfc4ab;border:1px dashed #d8b15e55;background:#d8b15e0d;
  padding:5px 10px;margin-top:8px;line-height:1.6}
.votestrip b{color:var(--gold)}
.votestrip.sway{border-color:var(--flag);color:#e6c98a}
svg.wire{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:2}
svg.wire line{stroke:var(--gold);stroke-width:2.5;stroke-dasharray:600;stroke-dashoffset:600;
  filter:drop-shadow(0 0 4px #d8b15e);animation:draw .9s ease forwards .35s}
@keyframes draw{to{stroke-dashoffset:0}}
.reason-strip{font-size:11.5px;color:#bfb49a;padding:8px 10px 0;line-height:1.7;
  border-top:1px solid #ffffff14;margin-top:8px}
.reason-strip b{color:var(--gold)}

/* 下：判断与审核 */
.review{background:var(--paper);overflow-y:auto;padding:16px 22px}
.review h2{font-size:12px;letter-spacing:.35em;color:var(--accent);border-bottom:2px solid var(--line);
  padding-bottom:6px;margin-bottom:12px}
.audit-card{background:var(--card);border:1px solid var(--line);padding:14px 18px;font-size:13px;
  line-height:1.9}
.audit-card .v{display:inline-block;font-weight:900;padding:1px 12px;border-radius:3px;
  margin-right:10px;letter-spacing:.2em}
.audit-card .v.ok{color:var(--ok);border:2px solid var(--ok)}
.audit-card .v.flag{color:#fff;background:var(--flag)}
.audit-card .gap{color:#8a6d1f;margin-top:8px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
table.states{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--card)}
table.states td{border:1px solid var(--line);padding:6px 9px}
table.states td.k{color:var(--muted);width:96px;white-space:nowrap}
.chg{color:var(--accent);font-weight:700}
.commit-line{margin-top:12px;background:var(--card);border:1px solid var(--line);padding:10px 16px;
  font-size:13px}
.commit-line b{font-size:24px;color:var(--accent);font-family:var(--sans)}
.hint{color:var(--muted);font-size:12px;padding:20px;text-align:center}
"""

JS = r"""
// 名单制适配①：演员列由 CAST 数组驱动（蓝本硬编码 ['周默','沈雯']）。
const PALETTE=['#4a6d8c','#8c4a5e','#6d8c4a','#8c7a4a','#4a8c7e','#7e4a8c'];
const KIND_RL={candidate:'候选人 · 试用期新人',counterpart:'对位 · 直属上级',colleague:'同事 · 团队成员'};
const COLORS={};
CAST.forEach((c,i)=>{COLORS[c.name]=PALETTE[i%PALETTE.length]});
const KIND_ORDER={candidate:-1,counterpart:0,colleague:1};
const CAST_SORTED=CAST.slice().sort((a,b)=>(KIND_ORDER[a.kind]??9)-(KIND_ORDER[b.kind]??9));
const CAST_NAMES=CAST.map(c=>c.name);
let steps=[],cur=0,timer=null;

function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML}

function buildSteps(){
  TRACE.scenes.forEach(sc=>{
    steps.push({t:'open',sc});
    (sc.beats||[]).forEach(bt=>steps.push({t:'beat',sc,bt}));
    steps.push({t:'settle',sc});
  });
}

function npcList(sc){const a=sc.scene&&sc.scene.npc;return Array.isArray(a)?a.filter(x=>x&&!CAST_NAMES.includes(x)):[]}

function tocRender(){
  const el=document.getElementById('toc');let h='';
  steps.forEach((st,i)=>{
    if(st.t==='open')h+=`<div class="scene-h" onclick="go(${i})">第 ${st.sc.index} 幕 · ${esc(st.sc.turning_point.title)}</div>`;
    else if(st.t==='beat')h+=`<div class="step" data-i="${i}" onclick="go(${i})">回合 ${st.bt.beat} · ${esc(st.bt.acting_agent)}${st.bt.audit&&st.bt.audit.verdict==='黄旗'?' ⚑':''}</div>`;
    else h+=`<div class="step" data-i="${i}" onclick="go(${i})">收场 · 状态灯/承诺</div>`;
  });
  el.innerHTML=h;
}

function actorHtml(name,role,acting,isNpc,inner){
  const init=name.charAt(0);
  const tab=isNpc?'<span class="innertab disabled">布景 · 非 agent</span>'
    :`<span class="innertab" onclick="toggleInner(event,'${name}')">内 心 ▾</span>`;
  let panel='';
  if(!isNpc){
    let body;
    if(inner){
      const emos=Object.entries(inner.emotions||{}).map(([k,v])=>
        typeof v==='number'?`<div class="emo">${esc(k)}<span class="bar"><i style="width:${Math.min(100,v)}%"></i></span>${v}</div>`:'').join('');
      body=emos+`<div class="thought">${esc(inner.internal_thoughts||'（无）')}</div>`;
    }else body='<div class="none">本回合非行动方，无内心记录（引擎只为行动方生成情绪评价）。</div>';
    panel=`<div class="innerpanel" id="inner-${name}"><div class="ttl">${esc(name)} · 内 心 密 档</div>${body}</div>`;
  }
  return `<div class="actor ${acting?'acting':''} ${isNpc?'npc':''}" id="actor-${name}">
    <div class="ava" style="background:${COLORS[name]||'#4a4338'}">${esc(init)}</div>
    <div class="nm">${esc(name)}</div><div class="rl">${esc(role)}</div>${tab}${panel}</div>`;
}

function votesStrip(bt){
  const vs=bt.vote_summary;if(!vs)return'';
  const seq=(bt.votes||[]).map(v=>`第${v.round}问→原${v.orig_id}（呈现位${v.position}）`).join(' · ');
  const sway=vs.verdict==='摇摆';
  return `<div class="votestrip ${sway?'sway':''}">🗳 换序三问表决（防位置偏置）：${esc(seq)} ⇒ <b>${esc(vs.verdict)}</b>，取原${esc(vs.winner_orig_id)}</div>`;
}

function render(){
  const st=steps[cur];if(!st)return;
  document.querySelectorAll('.toc .step,.toc .scene-h').forEach(e=>e.classList.remove('active'));
  const tocEl=document.querySelector(`.toc [data-i="${cur}"]`);if(tocEl)tocEl.classList.add('active');
  document.getElementById('stage-no').textContent=`第 ${st.sc.index} 幕 / ${st.t==='beat'?('回合 '+st.bt.beat):(st.t==='open'?'开 场':'收 场')}`;
  const stage=document.getElementById('stage'),review=document.getElementById('review');
  if(st.t==='open'){
    stage.innerHTML=`<div class="titlecard"><div class="no">第 ${st.sc.index} 幕 · ${esc(st.sc.turning_point.category)}</div>
      <h2>${esc(st.sc.turning_point.title)}</h2><p>${esc(st.sc.scene.setting||'')}</p>
      <p style="margin-top:10px">${esc(st.sc.scene.current_scene||'')}</p></div>`;
    review.innerHTML=`<div class="hint">开场字幕卡 —— 下一步进入回合。冲突：${esc(st.sc.scene.scene_conflict||'')}</div>`;
    return;
  }
  if(st.t==='settle'){
    const cons=(st.sc.consequences||[]).map(c=>`· ${esc(c.matter)} → ${esc(c.outcome)}`).join('<br>');
    // 名单制适配②：收场卡渲染 relations 关系细目
    const rels=Object.entries(st.sc.relations||{}).map(([nm,r])=>`· ${esc(nm)}：${esc(r.attitude||'?')}——${esc(r.evidence||'')}`).join('<br>');
    stage.innerHTML=`<div class="settlecard"><div class="tag">📋 本 幕 收 场</div>
      <p>${esc(st.sc.scene_summary||'')}</p>${cons?`<div class="cons"><b>后果结算（入台账）：</b><br>${cons}</div>`:''}
      ${rels?`<div class="rels"><b>关系细目（只入档不进灯）：</b><br>${rels}</div>`:''}</div>`;
    let rows='';
    STATE_KEYS.forEach(k=>{
      const ch=st.sc.state_changes&&st.sc.state_changes[k];
      const v=ch?`<span class="chg">${esc(ch[0])} → ${esc(ch[1])}</span>`:esc(st.sc.states[k]);
      rows+=`<tr><td class="k">${esc(STATE_LABELS[k])}</td><td>${v}</td><td>${esc((st.sc.evidence||{})[k]||'')}</td></tr>`;
    });
    const warn=(st.sc.warnings||[]).length?`<div class="commit-line" style="border-left:5px solid var(--flag)">⚠ ${esc(st.sc.warnings.join('；'))}</div>`:'';
    review.innerHTML=`<h2>判 断 · 状 态 灯 与 承 诺</h2><div class="grid2">
      <table class="states">${rows}</table>
      <div><div class="commit-line"><b>${esc(st.sc.commitment)}</b> / 5 留任-契合承诺<br>
      <span style="color:var(--muted)">${esc(st.sc.commitment_rationale||'')}</span></div>${warn}</div></div>`;
    return;
  }
  // beat：候选人居左、其余真 agent 按 kind 排列、场景 npc 灰头像缀尾
  const bt=st.bt,dec=bt.decision||{},audit=bt.audit||{},appr=bt.appraisal||{};
  const cast=[
    ...CAST_SORTED.map(c=>actorHtml(c.name,KIND_RL[c.kind]||c.role||'',bt.acting_agent===c.name,false,
      bt.acting_agent===c.name?appr:null)),
    ...npcList(st.sc).map(n=>actorHtml(n,'场景 · NPC（布景）',false,true,null))
  ].join('');
  const o2c={},vtally={};
  (bt.options||[]).forEach(o=>{o2c[o.orig_id]=o.id});
  (bt.votes||[]).forEach(v=>{vtally[v.orig_id]=(vtally[v.orig_id]||0)+1});
  const opts=(bt.options||[]).map(o=>{
    const n=vtally[o.orig_id]||0;const dots=n?`<span class="vts" title="换序三问得 ${n} 票">${'●'.repeat(n)}</span>`:'';
    return `<div class="opt ${o.id===dec.action_id?'chosen':''}" id="opt-${o.id}">
    <span class="oid">${esc(o.id)}</span>${esc(o.text)}<span class="orig">原序${esc(o.orig_id||'?')}</span>${dots}</div>`}).join('');
  stage.innerHTML=`
    <div class="narr-strip">${esc(bt.narration)}</div>
    <div class="junc-strip">⚡ ${esc(bt.juncture)}</div>
    <div class="floor"><svg class="wire" id="wire"></svg>
      <div class="cast">${cast}</div>
      <div class="optbox"><div class="ttl">候 选 行 动（顺序已随机打乱 · 换序三问）</div>${opts}
        ${votesStrip(bt)}
        <div class="reason-strip"><b>${esc(bt.acting_agent)}</b> 选了 ${esc(dec.action_id)}（信心 ${esc(dec.confidence??'?')}）：${esc(dec.reasoning||'')}</div>
      </div></div>`;
  const fab=(audit.fabricated_cues||[]);
  const gap=audit.inner_gap||'无';
  const gapHtml=(gap!=='无'&&gap!=='')?`<div class="gap">心口缝（只记录不打分）：${esc(gap)}</div>`:'';
  review.innerHTML=`<h2>审 核 · 理 由 审 计（独立 AI，结构对账，只标记不改判）</h2>
    <div class="audit-card"><span class="v ${audit.verdict==='通过'?'ok':'flag'}">${esc(audit.verdict||'?')}</span>
    手册命中：${esc((audit.playbook_match||[]).join('、')||'无')}　|　手册冲突：${esc(audit.playbook_conflict||'无')}　|
    与内心：${esc(audit.thought_consistency||'?')}（${esc(audit.thought_note||'')}）　|
    编造线索：${esc(fab.length?fab.join('、'):'无')}　|　信息越权：${esc(audit.info_overreach||'无')}<br>${esc(audit.note||'')}${gapHtml}</div>`;
  requestAnimationFrame(()=>requestAnimationFrame(drawWire));
}

function drawWire(){
  const st=steps[cur];if(!st||st.t!=='beat')return;
  const dec=st.bt.decision||{};
  const a=document.getElementById('actor-'+st.bt.acting_agent);
  const o=document.getElementById('opt-'+dec.action_id);
  const svg=document.getElementById('wire');
  if(!a||!o||!svg)return;
  const fl=svg.getBoundingClientRect(),ra=a.querySelector('.ava').getBoundingClientRect(),ro=o.getBoundingClientRect();
  svg.setAttribute('viewBox',`0 0 ${fl.width} ${fl.height}`);
  svg.innerHTML=`<line x1="${ra.right-fl.left}" y1="${ra.top+ra.height/2-fl.top}"
    x2="${ro.left-fl.left}" y2="${ro.top+ro.height/2-fl.top}"/>`;
}

function toggleInner(ev,name){
  ev.stopPropagation();
  const p=document.getElementById('inner-'+name);if(!p)return;
  const was=p.classList.contains('open');
  document.querySelectorAll('.innerpanel').forEach(x=>x.classList.remove('open'));
  if(!was){p.classList.add('open');stopAuto()}   // 看心理时自动暂停（继承旧铁律 H）
}

function go(i){cur=Math.max(0,Math.min(steps.length-1,i));render()}
function next(){go(cur+1)}
function prev(){go(cur-1)}
function stopAuto(){if(timer){clearInterval(timer);timer=null;document.getElementById('btn-play').textContent='▶ 自动';document.getElementById('btn-play').classList.remove('playing')}}
function toggleAuto(){
  if(timer){stopAuto();return}
  timer=setInterval(()=>{if(cur>=steps.length-1)stopAuto();else next()},4500);
  document.getElementById('btn-play').textContent='⏸ 暂停';document.getElementById('btn-play').classList.add('playing');
}
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')next();if(e.key==='ArrowLeft')prev()});
window.addEventListener('resize',drawWire);
buildSteps();tocRender();render();
"""

STATE_LABELS = {
    "conflict": "冲突", "repair_outcome": "修复结果", "role_clarity": "角色清晰度",
    "embeddedness": "投入绑定", "alternatives": "外部机会", "transition": "变动",
    "network": "团队接纳", "exit_marker": "离职信号",
}


def build(run_dir: pathlib.Path) -> pathlib.Path:
    trace = json.loads((run_dir / "trace.json").read_text(encoding="utf-8"))
    m = trace["meta"]
    trace_js = json.dumps(trace, ensure_ascii=False).replace("</", "<\\/")
    labels_js = json.dumps(STATE_LABELS, ensure_ascii=False)
    keys_js = json.dumps(list(STATE_LABELS.keys()), ensure_ascii=False)
    cast_js = json.dumps(m.get("cast") or [], ensure_ascii=False)
    cand_js = json.dumps(m.get("candidate", ""), ensure_ascii=False)
    page = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>放映厅 · SPOILER — {run_dir.name}</title><style>{CSS}</style></head>
<body>
<div class="app">
  <aside class="console">
    <h1>SPOILER · 放映厅</h1>
    <div class="sub">CONTROLLED-OPTION ROLLOUT</div>
    <div class="meta">运行：{run_dir.name}<br>观察主体：{m.get('candidate', '?')}（候选人）<br>
      模型：{m['model']}　幕数：{m['n_scenes']}　调用：{m['n_llm_calls']} 次<br>
      行动方：{'、'.join(f'{k} {v} 次' for k, v in m.get('actor_counts', {}).items())}<br>
      审计黄旗：{m.get('audit_flags', 0)} 个　警告：{m['warnings_total']} 条</div>
    <div class="ctrl">
      <button onclick="prev()">⏮ 上一步</button>
      <button id="btn-play" onclick="toggleAuto()">▶ 自动</button>
      <button onclick="next()">⏭ 下一步</button>
    </div>
    <div class="toc" id="toc"></div>
    <div class="foot">⚠ 诚实脚注：回放=已录制 trace（非直播）；单 run 轨迹、人设手写合成（可为蒸馏产物）；
承诺为机制部件、未经对账校准，不构成预测；心理默认隐藏，点"内心"展开（展开即暂停）；
关系细目只入档不进灯；名单制多人：同事亦为真 agent；理由审计员同为 AI，结构对账供人复核。</div>
  </aside>
  <main class="main">
    <div class="stage-wrap">
      <div class="stage-head"><span>放 映 厅</span><span id="stage-no"></span></div>
      <div class="stage" id="stage"></div>
    </div>
    <div class="review" id="review"></div>
  </main>
</div>
<script>
const TRACE={trace_js};
const STATE_LABELS={labels_js};
const STATE_KEYS={keys_js};
const CAST={cast_js};
const CANDIDATE={cand_js};
{JS}
</script>
</body></html>"""
    out = run_dir / "放映厅.html"
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
