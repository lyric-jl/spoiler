# sandbox3/pages/theater.py
"""操作台/放映厅前端（单页，由 server.py 提供；数据全部走 /api/*）。
搬自蓝本 relate_mvp/theater_page.py（已验证资产），CSS/布局/表决条/心口缝金标/
聚合视图/诚实脚注整段保留；只做名单制六点适配（见模块尾注释）。
布局：左=控制台（导入名单/场景选项/场景共创/JD），右上=舞台（候选人居左、其余按
kind 排右列、导演+记录者顶部、中央选项卡+理由），右下=幕回合滚动列表+判断（左）/状态灯（右）。
口径（作者 2026-06-07 拍）：候选人头像下默认外显一句话心理，点开看全文；
名单制多人：同事亦为真 agent（金圈可行动、点开内心）；场景 npc 仍灰头像布景、点不开。"""

PAGE = r"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPOILER · 操作台</title>
<style>
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
.app{display:grid;grid-template-columns:330px 1fr;height:100vh}

/* ===== 左：控制台 ===== */
.console{background:var(--card);border-right:2px solid var(--line);display:flex;
  flex-direction:column;overflow:hidden}
.console h1{font-family:var(--serif);font-size:18px;font-weight:900;letter-spacing:.08em;
  padding:14px 16px 2px}
.console .sub{font-size:10.5px;color:var(--muted);padding:0 16px 8px;letter-spacing:.18em;
  border-bottom:1px solid var(--line)}
.panes{flex:1;overflow-y:auto}
details{border-bottom:1px solid var(--line)}
summary{cursor:pointer;font-size:12.5px;font-weight:700;letter-spacing:.15em;color:var(--accent);
  padding:10px 16px;user-select:none}
summary:hover{background:#00000006}
.pane{padding:4px 16px 14px;font-size:12px}
textarea,input[type=text],input[type=number],select{width:100%;font-family:var(--sans);font-size:12px;
  border:1px solid var(--line);background:#fff;padding:6px 8px;border-radius:3px;color:var(--ink)}
textarea{resize:vertical}
.btn{display:inline-block;font-size:12px;padding:6px 14px;cursor:pointer;border:none;
  background:var(--ink);color:#fff;border-radius:3px;letter-spacing:.1em;margin-top:8px}
.btn:hover{background:var(--accent)}
.btn.primary{background:var(--accent);font-weight:700;width:100%;padding:9px 0;font-size:14px}
.btn.primary:disabled{background:#9a8f7a;cursor:not-allowed}
.tip{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.6}
.row{display:flex;gap:8px;align-items:center;margin-top:8px}
.row label{font-size:11.5px;color:var(--muted);white-space:nowrap}
#chatlog{height:170px;overflow-y:auto;border:1px solid var(--line);background:#fff;
  padding:8px;font-size:12px;line-height:1.7;margin-bottom:6px}
#chatlog .me{color:var(--ink);margin:4px 0}
#chatlog .ai{color:#5a4a8a;margin:4px 0;font-family:var(--serif)}
#chatlog .me::before{content:"我：";color:var(--muted)}
#chatlog .ai::before{content:"模型：";color:var(--muted)}
.foot{font-size:10px;color:#5d4a1d;background:#f7e9c8;border-top:1px solid #dcbf7a;
  padding:8px 12px;line-height:1.6}
#prep-log{max-height:150px;overflow-y:auto;border:1px solid var(--line);background:#fff;
  padding:6px 8px;font-size:11px;line-height:1.6;margin:6px 0;color:#574e3f}
#prep-log .ln{padding:1px 0}
#prep-log .ln.err{color:var(--accent);font-weight:700}
#prep-ready{font-weight:700;color:var(--ok)}
.portrait-tip{font-size:10px;color:#5d4a1d;background:#f7e9c8;padding:5px 8px;margin-top:6px;line-height:1.6}

/* ===== 右 ===== */
.main{display:grid;grid-template-rows:minmax(0,56%) minmax(0,44%);overflow:hidden}
.stage-wrap{position:relative;background:var(--stage);overflow:hidden;
  border-bottom:4px double var(--gold)}
.stage-head{display:flex;justify-content:space-between;padding:8px 16px;font-size:11px;
  color:#bfb49a;letter-spacing:.2em}
.stage-head .live{color:#e25b4a;font-weight:700}
.stage{position:relative;height:calc(100% - 64px);display:grid;
  grid-template-columns:170px 1fr 150px;gap:10px;padding:0 18px 8px}
.thirdparty{position:absolute;top:-30px;left:50%;transform:translateX(-50%);display:flex;gap:22px;z-index:4}
.tp-actor{display:flex;flex-direction:column;align-items:center}
.tp-actor .ava{width:36px;height:36px;border-radius:50%;background:#3a3a4a;border:2px solid #555;
  display:flex;align-items:center;justify-content:center;font-family:var(--kai);font-size:15px;color:#cfc4ab}
.tp-actor.busy .ava{border-color:var(--gold);box-shadow:0 0 10px #d8b15e66}
.tp-actor .nm{font-size:9.5px;color:#8a7e6a;margin-top:2px}
.col{display:flex;flex-direction:column;justify-content:center;gap:12px;position:relative;z-index:3;
  padding-top:26px}
.actor{display:flex;flex-direction:column;align-items:center;cursor:pointer}
.ava{width:58px;height:58px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-family:var(--kai);font-size:24px;font-weight:700;color:#fff;border:3px solid #4a4032;
  transition:box-shadow .4s,border-color .4s}
.actor.acting .ava{border-color:var(--gold);box-shadow:0 0 18px #d8b15e88}
.actor .nm{font-size:11.5px;color:var(--stage-ink);margin-top:4px;letter-spacing:.1em}
.actor .rl{font-size:9.5px;color:#8a7e6a}
.actor.npc .ava{width:42px;height:42px;font-size:17px;background:#4a4338;border-color:#3a342b;cursor:default}
.oneliner{margin-top:6px;max-width:160px;font-family:var(--kai);font-size:12px;color:var(--gold);
  background:#d8b15e14;border:1px dashed #d8b15e55;padding:5px 8px;line-height:1.6;border-radius:3px}
.oneliner.empty{color:#6a614f;border-color:#4a4032}
.center{display:flex;flex-direction:column;min-height:0;padding-top:26px}
.optcard{flex:1;border:2px solid #d8b15e66;background:#ffffff08;padding:12px 16px;overflow-y:auto;min-height:0}
.optcard .scene-tag{font-size:10.5px;color:var(--gold);letter-spacing:.25em;margin-bottom:6px}
.optcard .narr{font-family:var(--serif);font-size:13.5px;color:#cfc4ab;line-height:1.85;margin-bottom:8px}
.optcard .junc{font-family:var(--serif);font-size:13px;color:#fff;background:#a3271d33;
  border-left:3px solid var(--accent);padding:5px 10px;margin-bottom:10px}
.opt{border:1px solid #ffffff2a;background:#ffffff0a;padding:7px 11px 7px 34px;margin:6px 0;
  font-family:var(--serif);font-size:12.5px;color:var(--stage-ink);position:relative;line-height:1.65}
.opt .oid{position:absolute;left:10px;top:6px;font-weight:900;color:#8a7e6a;font-size:12px;font-family:var(--sans)}
.opt.chosen{border-color:var(--gold);background:#d8b15e1c}
.opt.chosen .oid{color:var(--gold)}
.reasonbox{border:2px solid #c8a830;background:#c8a83014;margin-top:8px;padding:9px 13px;
  font-size:12px;color:#e6d9ad;line-height:1.7;display:none}
.reasonbox.show{display:block}
.reasonbox b{color:var(--gold)}
.votestrip{border:1px dashed #d8b15e55;background:#d8b15e0d;margin-top:6px;padding:6px 11px;
  font-size:11.5px;color:#cfc4ab;line-height:1.6}
.votestrip b{color:var(--gold)}
.votestrip.sway{border-color:var(--flag);background:#b07a1014;color:#e6c98a}
.votestrip .vnote{display:block;font-size:10px;color:#8a7e6a}
.opt .vts{color:var(--gold);font-size:10px;margin-left:8px;letter-spacing:2px;white-space:nowrap}
.opt .otag{color:#8a8576;font-size:10.5px;margin-left:8px;white-space:nowrap}
svg.wire{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:2}
svg.wire line{stroke:var(--gold);stroke-width:2.5;stroke-dasharray:600;stroke-dashoffset:600;
  filter:drop-shadow(0 0 4px #d8b15e);animation:draw .9s ease forwards .25s}
@keyframes draw{to{stroke-dashoffset:0}}
.statusline{height:24px;padding:0 18px;font-size:11.5px;color:var(--gold);font-family:var(--serif)}
.titlecard{position:absolute;inset:0;background:#16120d;display:flex;flex-direction:column;
  align-items:center;justify-content:center;z-index:10;color:var(--stage-ink);text-align:center;padding:0 70px}
.titlecard .no{font-size:12px;letter-spacing:.5em;color:var(--gold);margin-bottom:12px}
.titlecard h2{font-family:var(--serif);font-size:26px;font-weight:900;letter-spacing:.1em;margin-bottom:12px}
.titlecard p{font-family:var(--serif);font-size:13px;color:#bfb49a;line-height:1.9;max-width:640px}
.innerpanel{position:absolute;right:16px;top:34px;width:320px;background:var(--stage2);
  border:1px solid var(--gold);padding:12px 14px;z-index:30;box-shadow:0 6px 24px #000a;display:none}
.innerpanel.open{display:block}
.innerpanel .ttl{font-size:11px;color:var(--gold);letter-spacing:.3em;margin-bottom:8px}
.innerpanel .thought{font-family:var(--kai);font-size:14px;color:var(--stage-ink);line-height:1.9}
.innerpanel .emo{display:flex;align-items:center;gap:6px;font-size:11px;color:#bfb49a;margin:3px 0}
.innerpanel .bar{flex:1;height:5px;background:#ffffff1f;border-radius:3px;overflow:hidden}
.innerpanel .bar i{display:block;height:100%;background:var(--gold)}
.innerpanel .x{position:absolute;right:10px;top:8px;cursor:pointer;color:#8a7e6a}

.bottom{display:grid;grid-template-columns:1fr 1fr;gap:0;overflow:hidden}
.bl{display:grid;grid-template-rows:1fr 1fr;border-right:2px solid var(--line);overflow:hidden}
.panel{overflow-y:auto;padding:10px 16px}
.panel h2{font-size:11px;letter-spacing:.3em;color:var(--accent);border-bottom:2px solid var(--line);
  padding-bottom:4px;margin-bottom:8px;background:var(--paper);position:sticky;top:0}
.panel h2.nosticky{position:static;margin-top:14px}
#history .item{font-size:12px;padding:4px 8px;cursor:pointer;border-left:3px solid transparent;color:#574e3f}
#history .item:hover{background:#00000008}
#history .item.active{border-left-color:var(--accent);background:#a3271d12;font-weight:700}
#history .item .flag{color:var(--flag)}
#judge .j{font-size:12px;line-height:1.7;padding:5px 8px;border-bottom:1px dashed var(--line)}
#judge .j .v{font-weight:900;padding:0 6px;border-radius:2px;margin-right:6px}
#judge .j .v.ok{color:var(--ok);border:1px solid var(--ok)}
#judge .j .v.flag{color:#fff;background:var(--flag)}
#judge .j .v.gap{color:#8a6d1f;border:1px solid var(--gold);background:#d8b15e22}
#judge .j.settle{background:#fbf7ec}
.relrow{font-size:11px;color:#6a614f;margin-top:3px;padding-left:4px}
table.states{width:100%;border-collapse:collapse;font-size:12px;background:var(--card)}
table.states td{border:1px solid var(--line);padding:5px 8px}
table.states td.k{color:var(--muted);width:88px;white-space:nowrap}
.chg{color:var(--accent);font-weight:700}
.commitbar{margin:10px 0;font-size:13px}
.commitbar b{font-size:22px;color:var(--accent)}
.autofollow{font-size:11px;color:var(--muted);padding:4px 8px}
</style></head>
<body>
<div class="app">
<aside class="console">
  <h1>SPOILER · 操作台</h1>
  <div class="sub">CONTROLLED-OPTION ROLLOUT · LIVE</div>
  <div class="panes">
    <details open>
      <summary>⓪ 案例配置（JD 驱动）</summary>
      <div class="pane">
        <div class="row"><label>岗位 JD</label><select id="jd-sel"></select></div>
        <div class="row"><label>候选人</label><select id="cv-sel"></select></div>
        <button class="btn" onclick="prepare('live')">▶ 现做（出题→答卷→蒸馏→搭班→场景）</button>
        <button class="btn" onclick="prepare('load')">⚡ 秒加载预备案例</button>
        <div class="tip" id="prep-ready"></div>
        <div id="prep-log" style="display:none"></div>
        <div class="tip">"现做"全程真调大模型、几十次调用要等几分钟（后台跑、上方报进度）；
          备过的案例用"秒加载"瞬间复现。完成后名单/场景/画像自动就位，再去②开拍。</div>
      </div>
    </details>
    <details id="portrait-details">
      <summary>候选人画像（九维）</summary>
      <div class="pane" id="portrait-pane">
        <div class="tip">备料完成后，这里显示候选人按 JD 测评得到的九维倾向画像。</div>
      </div>
    </details>
    <details>
      <summary>① 导入名单（cast）</summary>
      <div class="pane">
        <div class="tip" id="cast-now">当前：内置名单</div>
        <textarea id="cast-json" rows="6" placeholder='{"cast":[{"name":"…","kind":"candidate","role":"…","persona":"…","playbook":["…","…","…"]},{"name":"…","kind":"counterpart",…}]}'></textarea>
        <button class="btn" onclick="importCast()">导入名单</button>
        <span class="tip" id="cast-msg"></span>
        <div class="tip">kind 须含且仅含一个 candidate（观察主体）；其余 counterpart/colleague。</div>
      </div>
    </details>
    <details open>
      <summary>② 场景与开拍</summary>
      <div class="pane">
        <div class="row"><label>起始场景</label><select id="scene-sel"></select></div>
        <div class="row"><label>幕数</label><input type="number" id="n-scenes" value="2" min="1" max="6">
          <label>种子</label><input type="number" id="seed" placeholder="可空"></div>
        <button class="btn primary" id="btn-run" onclick="startRun()">▶ 开始推演（直播）</button>
        <div class="tip">直播=每步等真实生成，画面间有真实等待；不许用假动画掩盖。</div>
      </div>
    </details>
    <details>
      <summary>③ 场景共创（大模型接口）</summary>
      <div class="pane">
        <div id="chatlog"></div>
        <textarea id="chat-in" rows="2" placeholder="向模型描述你想推演的场景，它会提问、同步想法"></textarea>
        <button class="btn" onclick="sendChat()">发送</button>
        <button class="btn" onclick="crystallize()">把共创结果存为自定义场景</button>
        <span class="tip" id="chat-msg"></span>
      </div>
    </details>
    <details>
      <summary>④ JD 自由文本（遗留）</summary>
      <div class="pane">
        <textarea id="jd" rows="4" placeholder="自由文本 JD 暂存框（遗留入口）——JD 驱动请用上面的 ⓪"></textarea>
        <button class="btn" onclick="saveJd()">暂存</button>
        <span class="tip" id="jd-msg"></span>
      </div>
    </details>
  </div>
  <div class="foot">⚠ 诚实脚注：单 run 轨迹、人设合成；承诺为机制部件、未经对账校准，不构成预测；
候选人一句话心理默认外显（作者 2026-06-07 拍），点头像看全文；审计员同为 AI，结构对账供人复核；
每个选择经换序三问取多数票（防位置偏置），模型层偏好分布如实入档；
名单制多人：同事亦为真 agent（金圈可行动、点开内心），关系细目只入档不进灯。</div>
</aside>
<main class="main">
  <div class="stage-wrap">
    <div class="stage-head"><span>放 映 厅</span><span id="live-tag"></span><span id="stage-no">待 机</span></div>
    <div class="stage" id="stage">
      <div class="thirdparty">
        <div class="tp-actor" id="tp-director"><div class="ava">导</div><div class="nm">场景导演</div></div>
        <div class="tp-actor" id="tp-recorder"><div class="ava">记</div><div class="nm">记录者</div></div>
      </div>
      <div class="col" id="col-left"></div>
      <div class="center" id="center"><div class="optcard"><div class="narr" style="color:#6a614f">
        左侧「场景与开拍」选好场景，点「开始推演」。</div></div></div>
      <div class="col" id="col-right"></div>
      <svg class="wire" id="wire"></svg>
      <div class="innerpanel" id="innerpanel"></div>
    </div>
    <div class="statusline" id="statusline"></div>
  </div>
  <div class="bottom">
    <div class="bl">
      <div class="panel"><h2>幕 · 回 合（点击回看）<span class="autofollow"><label><input type="checkbox" id="follow" checked> 跟随直播</label></span></h2><div id="history"></div></div>
      <div class="panel"><h2>简 要 判 断</h2><div id="judge"></div></div>
    </div>
    <div class="panel"><h2>状 态 灯</h2><div id="states"></div>
      <h2 class="nosticky">📊 5-RUN 聚 合</h2><div id="agg"></div></div>
  </div>
</main>
</div>
<script>
const STATE_LABELS={"conflict":"冲突","repair_outcome":"修复结果","role_clarity":"角色清晰度",
"embeddedness":"投入绑定","alternatives":"外部机会","transition":"变动","network":"团队接纳","exit_marker":"离职信号"};
const PALETTE=['#4a6d8c','#8c4a5e','#6d8c4a','#8c7a4a','#4a8c7e','#7e4a8c'];
const KIND_LABEL={candidate:'候选人 · 试用期新人',counterpart:'对位 · 直属上级',colleague:'同事 · 团队成员'};
const COLORS={};
let events=[],viewIdx=-1,running=false,cast=[],candidate='',chatMsgs=[];

function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML}
function firstSentence(s){if(!s)return'';const m=String(s).split(/(?<=[。！？!?])/);return m[0]||String(s).slice(0,40)}

// 名单驱动：候选人居左，其余按 kind 排右列（counterpart 在前，colleague 在后），保原顺序。
function applyCast(list){
  cast=list||[];
  COLORS.length=0;for(const k in COLORS)delete COLORS[k];
  cast.forEach((c,i)=>{COLORS[c.name]=PALETTE[i%PALETTE.length]});
  const cand=cast.find(c=>c.kind==='candidate');candidate=cand?cand.name:(cast[0]?cast[0].name:'');
}
function leftCol(){return cast.filter(c=>c.kind==='candidate')}
function rightCol(){const order={counterpart:0,colleague:1};
  return cast.filter(c=>c.kind!=='candidate').sort((a,b)=>(order[a.kind]??9)-(order[b.kind]??9))}

async function api(path,body){
  const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)}:undefined);
  return await r.json();
}

/* ---- 控制台 ---- */
async function loadState(){
  const s=await api('/api/state');
  running=s.running;
  applyCast(s.cast||[]);
  const tags=cast.map(c=>`${esc(c.name)}（${esc(c.kind)}）`).join(' × ');
  document.getElementById('cast-now').innerHTML=`当前：${tags||'内置名单'}`;
  const sel=document.getElementById('scene-sel');sel.innerHTML='';
  s.scenes.forEach(t=>{const o=document.createElement('option');o.value=t.id;
    o.textContent=`${t.id} [${t.category}] ${t.title}`;sel.appendChild(o)});
  document.getElementById('btn-run').disabled=running;
  document.getElementById('live-tag').innerHTML=running?'<span class="live">● 直播中</span>':'';
}
async function startRun(){
  const body={scenes:+document.getElementById('n-scenes').value||2,
    start:document.getElementById('scene-sel').value,
    seed:document.getElementById('seed').value?+document.getElementById('seed').value:null};
  const r=await api('/api/run',body);
  if(r.error){alert(r.error);return}
  events=[];viewIdx=-1;running=true;
  document.getElementById('btn-run').disabled=true;
  document.getElementById('live-tag').innerHTML='<span class="live">● 直播中</span>';
}
async function importCast(){
  const el=document.getElementById('cast-msg');
  try{
    const j=JSON.parse(document.getElementById('cast-json').value);
    const r=await api('/api/import_cast',j);
    if(r.error){el.textContent='✗ '+r.error;return}
    el.textContent='✓ 已导入 '+(r.cast||[]).length+' 人';loadState();
  }catch(e){el.textContent='✗ JSON 解析失败：'+e.message}
}
async function sendChat(){
  const inp=document.getElementById('chat-in'),log=document.getElementById('chatlog');
  const t=inp.value.trim();if(!t)return;
  chatMsgs.push({role:'user',content:t});
  log.innerHTML+=`<div class="me">${esc(t)}</div>`;inp.value='';
  log.innerHTML+=`<div class="ai" id="chat-wait">…思考中</div>`;log.scrollTop=log.scrollHeight;
  const r=await api('/api/chat',{messages:chatMsgs});
  document.getElementById('chat-wait').remove();
  if(r.error){log.innerHTML+=`<div class="ai">（出错：${esc(r.error)}）</div>`;return}
  chatMsgs.push({role:'assistant',content:r.reply});
  log.innerHTML+=`<div class="ai">${esc(r.reply)}</div>`;log.scrollTop=log.scrollHeight;
}
async function crystallize(){
  const el=document.getElementById('chat-msg');
  if(chatMsgs.length<2){el.textContent='先和模型聊出个场景再存';return}
  el.textContent='…结晶中';
  const r=await api('/api/crystallize',{messages:chatMsgs});
  if(r.error){el.textContent='✗ '+r.error;return}
  el.textContent=`✓ 已入库：${r.scene.id}「${r.scene.title}」`;
  await loadState();document.getElementById('scene-sel').value=r.scene.id;
}
async function saveJd(){
  const r=await api('/api/jd',{text:document.getElementById('jd').value});
  document.getElementById('jd-msg').textContent=r.ok?'✓ 已暂存（遗留自由文本框；JD 驱动请用 ⓪）':('✗ '+r.error);
}

/* ---- ⓪ JD 驱动：配置案例→备料（现做/秒加载）→画像上墙 ---- */
let prepTimer=null;
async function loadCases(){
  let c;try{c=await api('/api/cases')}catch(e){return}
  if(!c||c.error)return;
  const js=document.getElementById('jd-sel'),cs=document.getElementById('cv-sel');
  js.innerHTML='';(c.samples.jd||[]).forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n;js.appendChild(o)});
  cs.innerHTML='';(c.samples.cv||[]).forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n;cs.appendChild(o)});
}
async function prepare(mode){
  const jd=document.getElementById('jd-sel').value,cv=document.getElementById('cv-sel').value;
  const rd=document.getElementById('prep-ready');
  if(!jd||!cv){rd.innerHTML='<span style="color:var(--accent)">✗ 先选 JD 和候选人</span>';return}
  rd.textContent=mode==='load'?'⚡ 秒加载中…':'▶ 已下令现做，后台备料中…';
  const r=await api('/api/prepare',{jd,cv,mode});
  if(r.error){rd.innerHTML='<span style="color:var(--accent)">✗ '+esc(r.error)+'</span>';return}
  if(mode!=='load'){const log=document.getElementById('prep-log');log.style.display='block';log.innerHTML='';}
  pollPrep();
}
async function pollPrep(){
  let p;try{p=await api('/api/prep_state')}catch(e){prepTimer=setTimeout(pollPrep,1500);return}
  const log=document.getElementById('prep-log');
  if(p.log&&p.log.length){log.style.display='block';
    log.innerHTML=p.log.map(l=>`<div class="ln ${/^✗/.test(l)?'err':''}">${esc(l)}</div>`).join('');
    log.scrollTop=log.scrollHeight;}
  if(p.error){document.getElementById('prep-ready').innerHTML=
    '<span style="color:var(--accent)">✗ 备料失败（见下方日志）</span>';return}
  if(p.ready){renderPortrait(p.portrait);
    document.getElementById('prep-ready').innerHTML='✓ 已就位：'+esc((p.meta&&p.meta.job)||'')+
      ' · 名单 '+((p.meta&&p.meta.n_cast)||'?')+' 人 · 场景 '+((p.meta&&p.meta.n_scenes)||'?')+' 幕';
    await loadState();return}
  if(p.running)prepTimer=setTimeout(pollPrep,1500);
}
function renderPortrait(pt){
  const el=document.getElementById('portrait-pane');
  if(!pt||!pt.scores){el.innerHTML='<div class="tip">（暂无画像）</div>';return}
  const det=document.getElementById('portrait-details');if(det)det.open=true;
  const rows=pt.scores.map(s=>{
    const lean=s.lean!=null?`${esc(s.lean_label)}（${esc(s.lean)}）`:'未知';
    const nq=s.n_questions!=null?s.n_questions:((s.n_good||0)+(s.n_bad||0));
    const probe=s.probe_rounds?`${nq}（追${s.probe_rounds}轮：${esc((s.probe_trail||[]).join('→'))}）`:`${nq}`;
    return `<tr><td class="k">${esc(s.dim)}</td><td style="color:var(--muted)">${esc(s.risk)}</td>
      <td><b>${lean}</b></td><td>${esc(s.confidence)}</td><td>${probe}</td></tr>`}).join('');
  el.innerHTML=`<div style="font-size:11.5px;color:var(--muted);margin-bottom:4px">候选人：<b>${esc(pt.name||'')}</b>`+
    `（${esc(pt.cv_id||'')}）· 出题源 ${esc(pt.jd_id||'')}</div>`+
    `<table class="states"><tr><td class="k">维度</td><td>风险</td><td>倾向</td><td>置信</td><td>题量（追题）</td></tr>${rows}</table>`+
    `<div class="portrait-tip">⚠ 倾向＝她"答出来的样子"、非真实风险高低；模型扮演候选人作答、非真人，不构成预测。`+
    `低置信是常态（自陈天生薄）。题量带「追N轮」＝作答飘、系统自动加题探测；追满仍飘则诚实判低。</div>`;
}

/* ---- 5-run 聚合视图（数据来自命令行 aggregate 的最新批次） ---- */
async function loadAgg(){
  const el=document.getElementById('agg');
  let a;
  try{a=await api('/api/batch_latest')}catch(e){el.innerHTML='✗ 聚合接口不可达';return}
  if(a.empty){el.innerHTML='<div style="color:var(--muted);font-size:11.5px;padding:4px">'+
    '暂无批量数据——命令行跑 python -m sandbox3.aggregate 后<a href="#" onclick="loadAgg();return false">刷新</a>。</div>';return}
  if(a.error){el.innerHTML=`<div style="color:var(--accent);font-size:11.5px">✗ ${esc(a.error)}</div>`;return}
  const commit=(a.commitment_trajectory||[]).map(c=>`第${c.scene}幕 ${c.mean}（${c.min}~${c.max}）`).join(' → ');
  const lights=Object.entries(a.final_lights||{}).map(([k,v])=>{
    const dist=Object.entries(v.dist).map(([val,n])=>`${val}×${n}`).join(' ');
    return `<tr><td class="k">${esc(STATE_LABELS[k]||k)}</td><td><b>${esc(v.mode)}</b></td>
      <td style="color:var(--muted)">${esc(dist)}</td></tr>`}).join('');
  const gaps=Object.entries(a.inner_gap_by_actor||{}).map(([k,v])=>`${k} ${v}`).join('、')||'无';
  el.innerHTML=`
    <div style="font-size:11.5px;color:var(--muted)">批次 ${esc(a.batch)} · ${a.n_runs} 局 · ${a.beats_total} 节骨眼
      　<a href="#" onclick="loadAgg();return false">刷新</a></div>
    <div style="font-size:12px;margin:6px 0">承诺轨迹（均值·极差）：${esc(commit)}</div>
    <table class="states">${lights}</table>
    <div style="font-size:12px;margin-top:8px;line-height:1.8">
      拉扯度：全票 ${a.vote_stats['全票']} · 多数票 ${a.vote_stats['多数票']} · 摇摆 ${a.vote_stats['摇摆']}
      （摇摆率 ${Math.round((a.sway_rate||0)*100)}%）——全票=想都不用想，分票=心里打架<br>
      审计黄旗率 ${Math.round((a.audit_flag_rate||0)*100)}%　心口缝 ${a.inner_gaps_total} 处（${esc(gaps)}，只记录不打分）</div>
    <div style="font-size:10px;color:#5d4a1d;background:#f7e9c8;padding:6px 8px;margin-top:6px;line-height:1.6">⚠ ${esc(a.footnote||'')}</div>`;
}

/* ---- 事件轮询 ---- */
async function poll(){
  try{
    const r=await api('/api/events?since='+events.length);
    if(r.events&&r.events.length){
      events.push(...r.events);
      if(document.getElementById('follow').checked)viewIdx=events.length-1;
      render();
    }
    const done=events.some(e=>e.type==='done'||e.type==='error');
    if(done&&running){running=false;document.getElementById('btn-run').disabled=false;
      document.getElementById('live-tag').textContent='已收官';}
  }catch(e){}
  setTimeout(poll,1200);
}

/* ---- 回放重建：把 events[0..viewIdx] 折成上下文 ---- */
function buildCtx(){
  const c={status:'',scene:null,beat:null,inner:{},lastInnerAll:{},settle:null,states:null,
    judges:[],history:[],npc:[]};
  for(let i=0;i<=viewIdx&&i<events.length;i++){
    const e=events[i];
    if(e.type==='status')c.status=e.text;
    else if(e.type==='run_started'){applyCast(e.cast||[]);if(e.candidate)candidate=e.candidate}
    else if(e.type==='scene_open'){c.scene=e;c.beat=null;c.inner={};c.settle=null;c.npc=e.npc||[];
      c.history.push({i,label:`第 ${e.scene} 幕 · ${e.tp.title}`,head:true})}
    else if(e.type==='beat_open'){c.beat=e;c.inner={};c.settle=null;
      c.history.push({i,label:`　回合 ${e.beat} · ${e.actor}`})}
    else if(e.type==='inner'){c.inner[e.actor]=e;c.lastInnerAll[e.actor]=e}
    else if(e.type==='decision'){if(c.beat&&c.beat.beat===e.beat)c.beat={...c.beat,decision:e}}
    else if(e.type==='audit'){
      if(c.beat&&c.beat.beat===e.beat)c.beat={...c.beat,audit:e};
      c.judges.push({kind:'audit',e});
      if(e.verdict==='黄旗'){const h=c.history[c.history.length-1];if(h&&!h.flag)h.flag=true}}
    else if(e.type==='settle'){c.settle=e;c.states=e;c.judges.push({kind:'settle',e});
      c.history.push({i,label:`　收场 · 状态灯/承诺`})}
    else if(e.type==='done'){c.history.push({i,label:`■ 全场结束（${e.meta.n_llm_calls} 次调用）`,head:true})}
    else if(e.type==='error'){c.history.push({i,label:`✗ 出错：${e.text}`,head:true})}
  }
  return c;
}

function actorHtml(name,role,acting,isNpc,oneliner){
  const ol=isNpc?'':(oneliner
    ?`<div class="oneliner">💭 ${esc(firstSentence(oneliner))}</div>`
    :`<div class="oneliner empty">（尚无内心记录）</div>`);
  return `<div class="actor ${acting?'acting':''} ${isNpc?'npc':''}" id="actor-${esc(name)}"
    onclick="${isNpc?'':`showInner('${esc(name)}')`}">
    <div class="ava" style="background:${COLORS[name]||'#4a4338'}">${esc(name.charAt(0))}</div>
    <div class="nm">${esc(name)}</div><div class="rl">${esc(role)}</div>${ol}</div>`;
}

let lastInnerCache={};
function showInner(name){
  const e=lastInnerCache[name];const p=document.getElementById('innerpanel');
  let body;
  if(e){
    const emos=Object.entries(e.emotions||{}).map(([k,v])=>typeof v==='number'
      ?`<div class="emo">${esc(k)}<span class="bar"><i style="width:${Math.min(100,v)}%"></i></span>${v}</div>`:'').join('');
    body=emos+`<div class="thought">${esc(e.internal_thoughts||'（无）')}</div>`;
  }else body='<div class="thought" style="color:#8a7e6a">尚无内心记录。</div>';
  p.innerHTML=`<span class="x" onclick="this.parentNode.classList.remove('open')">✕ 关闭</span>
    <div class="ttl">${esc(name)} · 内 心 密 档（全文）</div>${body}`;
  p.classList.add('open');
}

function render(){
  const c=buildCtx();lastInnerCache=c.lastInnerAll;
  document.getElementById('statusline').textContent=running?('⏳ '+(c.status||'…')):'';
  document.getElementById('tp-director').classList.toggle('busy',running&&/导演/.test(c.status||''));
  document.getElementById('tp-recorder').classList.toggle('busy',running&&/记录者/.test(c.status||''));
  // 头像列：候选人居左，其余真 agent 按 kind 排右，场景 npc 灰头像缀右列尾
  const actor=c.beat?c.beat.actor:'';
  document.getElementById('col-left').innerHTML=leftCol().map(m=>
    actorHtml(m.name,KIND_LABEL[m.kind]||m.role||'',actor===m.name,false,
      (c.lastInnerAll[m.name]||{}).internal_thoughts)).join('');
  const rights=rightCol().map(m=>
    actorHtml(m.name,KIND_LABEL[m.kind]||m.role||'',actor===m.name,false,
      (c.lastInnerAll[m.name]||{}).internal_thoughts)).join('');
  const npcs=(c.npc||[]).slice(0,3).map(n=>actorHtml(n,'场景 · NPC（布景）',false,true,null)).join('');
  document.getElementById('col-right').innerHTML=rights+npcs;
  // 中央
  const ce=document.getElementById('center');
  const sn=document.getElementById('stage-no');
  if(!c.scene){sn.textContent='待 机';}
  else if(c.settle){
    sn.textContent=`第 ${c.scene.scene} 幕 / 收 场`;
    const rels=Object.entries(c.settle.relations||{}).map(([nm,r])=>
      `<div class="narr" style="color:#8a7e6a">${esc(nm)}：${esc(r.attitude||'?')}——${esc(r.evidence||'')}</div>`).join('');
    ce.innerHTML=`<div class="optcard"><div class="scene-tag">📋 本 幕 收 场${c.settle.sim_time?' · '+esc(c.settle.sim_time):''}</div>
      <div class="narr">${esc(c.settle.summary||'')}</div>
      <div class="narr" style="color:#bfb49a">本幕在场知情：${esc((c.settle.witnesses||[]).join('、')||'?')}　（台账按在场者隔离，缺席者不知晓）</div>
      ${rels?`<div class="narr" style="color:var(--gold)">关系细目（只入档不进灯）：</div>${rels}`:''}
      <div class="narr" style="color:#8a7e6a">${(c.settle.warnings||[]).map(w=>'⚠ '+esc(w)).join('<br>')}</div></div>`;
  }else if(c.beat){
    sn.textContent=`第 ${c.scene.scene} 幕 / 回合 ${c.beat.beat}`;
    const dec=c.beat.decision;
    // 换序三问可视化：orig_id→画面呈现序字母 + 每选项得票点
    const o2c={},vtally={};
    (c.beat.options||[]).forEach(o=>{o2c[o.orig_id]=o.id});
    if(dec&&dec.votes)dec.votes.forEach(v=>{vtally[v.orig_id]=(vtally[v.orig_id]||0)+1});
    const opts=(c.beat.options||[]).map(o=>{
      const n=vtally[o.orig_id]||0;
      const dots=n?`<span class="vts" title="换序三问中得 ${n} 票">${'●'.repeat(n)}</span>`:'';
      const tg=o.tag?`<span class="otag">—— ${esc(o.tag)}</span>`:'';   // 倾向标签（导演打标，只给旁观面板；演员看不到）
      return `<div class="opt ${dec&&o.id===dec.action_id?'chosen':''}"
      id="opt-${o.id}"><span class="oid">${esc(o.id)}</span>${esc(o.text)}${tg}${dots}</div>`}).join('');
    let votestrip='';
    if(dec&&dec.votes&&dec.votes.length){
      const seq=dec.votes.map(v=>`第${v.round}问→${esc(o2c[v.orig_id]||('原'+v.orig_id))}`).join(' · ');
      const vd=dec.vote_verdict||'?';
      votestrip=`<div class="votestrip ${vd==='摇摆'?'sway':''}">🗳 换序三问（防位置偏置）：${seq} ⇒ <b>${esc(vd)}</b>${vd==='摇摆'?'（三问三答案，按第1问行动；摇摆已入档）':''}
        <span class="vnote">每问以不同顺序提问、按内容取多数；字母按画面顺序标注，各问原序全量入档 trace</span></div>`;
    }
    ce.innerHTML=`<div class="optcard"><div class="scene-tag">选 项 卡 · [${esc(c.scene.tp.category)}] ${esc(c.scene.tp.title)}${c.scene.sim_time?' · '+esc(c.scene.sim_time):''}（顺序已打乱 · 换序三问）</div>
      <div class="narr">${esc(c.beat.narration)}</div>
      <div class="junc">⚡ ${esc(c.beat.juncture)}</div>${opts}</div>${votestrip}
      <div class="reasonbox ${dec?'show':''}" id="reasonbox">${dec?`<b>理由</b>（${esc(c.beat.actor)}，信心 ${esc(dec.confidence??'?')}）：${esc(dec.reasoning||'')}`:''}</div>`;
  }else{
    sn.textContent=`第 ${c.scene.scene} 幕 / 开 场`;
    ce.innerHTML=`<div class="optcard"><div class="scene-tag">第 ${c.scene.scene} 幕 · ${esc(c.scene.tp.category)} · ${esc(c.scene.tp.title)}${c.scene.sim_time?' · '+esc(c.scene.sim_time):''}</div>
      <div class="narr">${esc(c.scene.setting||'')}</div>
      <div class="narr">${esc(c.scene.current_scene||'')}</div>
      <div class="junc">冲突：${esc(c.scene.scene_conflict||'')}</div></div>`;
  }
  // 连线
  const svg=document.getElementById('wire');svg.innerHTML='';
  if(c.beat&&c.beat.decision){
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      const a=document.getElementById('actor-'+c.beat.actor);
      const o=document.getElementById('opt-'+c.beat.decision.action_id);
      const st=document.getElementById('stage');
      if(!a||!o)return;
      const fl=st.getBoundingClientRect(),ra=a.querySelector('.ava').getBoundingClientRect(),
        ro=o.getBoundingClientRect();
      svg.setAttribute('viewBox',`0 0 ${fl.width} ${fl.height}`);
      const fromLeft=c.beat.actor===candidate;
      svg.innerHTML=`<line x1="${(fromLeft?ra.right:ra.left)-fl.left}" y1="${ra.top+ra.height/2-fl.top}"
        x2="${(fromLeft?ro.left:ro.right)-fl.left}" y2="${ro.top+ro.height/2-fl.top}"/>`;
    }));
  }
  // 历史
  const hi=document.getElementById('history');
  hi.innerHTML=c.history.map(h=>`<div class="item"
     onclick="document.getElementById('follow').checked=false;viewIdx=${h.i};render()"
     style="${h.head?'font-weight:700;color:var(--accent)':''}">${esc(h.label)}${h.flag?' <span class="flag">⚑</span>':''}</div>`).join('');
  hi.scrollTop=hi.scrollHeight;
  // 简要判断
  document.getElementById('judge').innerHTML=c.judges.map(j=>{
    if(j.kind==='audit'){const e=j.e;
      const over=e.info_overreach&&e.info_overreach!=='无'?`　<span class="v flag">信息越权</span>${esc(e.info_overreach)}`:'';
      const gap=e.inner_gap&&e.inner_gap!=='无'?`　<span class="v gap">心口缝</span>${esc(e.inner_gap)}`:'';
      return `<div class="j"><span class="v ${e.verdict==='通过'?'ok':'flag'}">${esc(e.verdict)}</span>
        第${e.scene}幕回合${e.beat}：手册命中 ${esc((e.playbook_match||[]).join('、')||'无')}；
        与内心${esc(e.thought_consistency||'?')}。${esc(e.note||'')}${over}${gap}</div>`}
    const e=j.e;
    const rels=Object.entries(e.relations||{}).map(([nm,r])=>
      `<div class="relrow">· ${esc(nm)}：${esc(r.attitude||'?')}——${esc(r.evidence||'')}</div>`).join('');
    return `<div class="j settle">📋 第${e.scene}幕收场：承诺 <b>${esc(e.commitment)}</b>/5 —— ${esc(e.rationale||'')}${rels}</div>`;
  }).join('');
  const jd=document.getElementById('judge');jd.scrollTop=jd.scrollHeight;
  // 状态灯
  if(c.states){
    let rows='';
    for(const k in STATE_LABELS){
      const ch=(c.states.changes||{})[k];
      const v=ch?`<span class="chg">${esc(ch[0])} → ${esc(ch[1])}</span>`:esc((c.states.states||{})[k]||'?');
      rows+=`<tr><td class="k">${esc(STATE_LABELS[k])}</td><td>${v}</td>
        <td style="color:var(--muted)">${esc((c.states.evidence||{})[k]||'')}</td></tr>`;
    }
    document.getElementById('states').innerHTML=
      `<div class="commitbar"><b>${esc(c.states.commitment)}</b> / 5 留任-契合承诺
       <span style="color:var(--muted)">${esc(c.states.rationale||'')}</span></div>
       <table class="states">${rows}</table>`;
  }else{
    document.getElementById('states').innerHTML='<div style="color:var(--muted);font-size:12px;padding:8px">首幕收场后点亮。</div>';
  }
}

loadState();poll();loadAgg();loadCases();pollPrep();
window.addEventListener('resize',()=>render());
</script>
</body></html>
"""
