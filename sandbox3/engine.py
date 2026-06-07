# sandbox3/engine.py
"""推演循环（名单制多人原生底座；蓝本=relate_mvp engine.py，机制行为等价迁移）。
机制清单：受控选项决策 / 换序三问取多数票 / 差量状态灯 / 防火墙（知情过滤）/
理由审计（独立调用）/ 台账时间线 / 后果结算 / ≥3灯黄旗。
依赖注入：run_simulation(cast=名单, llm=客户端, bank=场景库)——测试喂 FakeLLM，运行时唯一路径=DeepSeek live。"""
from __future__ import annotations
import random
import sys

from . import audit as AU
from .cast import Cast
from .config import MAX_BEATS, VOTE_ROUNDS
from .ledger import entry, ledger_text, visible
from .prompts import agent as PA
from .prompts import sm as PS
from .states import initial_state, apply_state_deltas, plausible_categories


def _log(msg: str) -> None:
    print(msg, flush=True)


def _coerce_options(raw) -> list[dict]:
    opts = []
    if isinstance(raw, list):
        for i, o in enumerate(raw):
            if isinstance(o, dict) and o.get("text"):
                opts.append({"id": str(o.get("id") or "ABCD"[i % 4]), "text": str(o["text"])})
    return opts


def _build_presentations(options: list[dict], rng: random.Random) -> list[list[dict]]:
    """洗牌一次得第1问呈现序，再逐问轮转——三问顺序互不相同、每个选项换坑位。
    每问按呈现位次重发 A/B/C/D，保留 orig_id 供对账。"""
    base = options[:]
    rng.shuffle(base)
    rounds = []
    for r in range(VOTE_ROUNDS):
        k = r % len(base)
        rot = base[k:] + base[:k]
        rounds.append([{"id": "ABCD"[i], "text": o["text"], "orig_id": o["id"]}
                       for i, o in enumerate(rot)])
    return rounds


def _tally_votes(votes: list[dict]) -> dict:
    """按内容（orig_id）计票：全票/多数票/摇摆（摇摆取第1问，入档是信号不是噪声）。"""
    tally: dict[str, int] = {}
    for v in votes:
        tally[v["orig_id"]] = tally.get(v["orig_id"], 0) + 1
    top = max(tally.values())
    verdict = "全票" if top == len(votes) else ("多数票" if top >= 2 else "摇摆")
    winner = next(v for v in votes if tally[v["orig_id"]] == top)
    return {"rounds": len(votes), "tally": tally, "verdict": verdict,
            "winner_orig_id": winner["orig_id"], "winner_round": winner["round"]}


AUDIT_VERDICTS = ("通过", "黄旗")


def _vote_decision(*, llm, cast: Cast, actor: str, internal_thoughts: str, scene: dict,
                   transcript: list[str], narration: str, juncture: str,
                   vis_ledger: list[dict], presentations: list[list[dict]],
                   warnings: list[str]) -> tuple[dict, list[dict], dict]:
    """换序三问：并发问 VOTE_ROUNDS 次（线程池），按内容取多数。
    官方决策 action_id 映射回第1问呈现序（页面展示序）。"""
    from concurrent.futures import ThreadPoolExecutor

    def ask(presented):
        return llm.complete_json(
            PA.decision_system(cast, actor),
            PA.decision_user(internal_thoughts, scene, transcript, narration,
                             juncture, vis_ledger, presented))
    with ThreadPoolExecutor(max_workers=len(presentations)) as ex:
        raw = list(ex.map(ask, presentations))
    votes, decs = [], []
    for rnd, (presented, dec) in enumerate(zip(presentations, raw), 1):
        if dec.get("action_id") not in {o["id"] for o in presented}:
            warnings.append(f"第{rnd}问 action_id 越界（{dec.get('action_id')!r}），落该问呈现序第一个")
            dec["action_id"] = presented[0]["id"]
        chosen = next(o for o in presented if o["id"] == dec["action_id"])
        votes.append({"round": rnd, "order": [o["orig_id"] for o in presented],
                      "position": dec["action_id"], "orig_id": chosen["orig_id"],
                      "reasoning": dec.get("reasoning", ""), "confidence": dec.get("confidence")})
        decs.append(dec)
    summary = _tally_votes(votes)
    if summary["verdict"] == "摇摆":
        warnings.append("换序三问答案各不相同（摇摆），取第1问的选择继续；摇摆已入档")
    dec = decs[summary["winner_round"] - 1]
    dec["action_id"] = next(o["id"] for o in presentations[0]
                            if o["orig_id"] == summary["winner_orig_id"])
    dec["chosen_orig_id"] = summary["winner_orig_id"]
    return dec, votes, summary


def _run_beat(*, llm, cast: Cast, beat_no: int, scene_idx: int, scene: dict, tp: dict,
              ledger: list[dict], state: dict, transcript: list[str],
              rng: random.Random, counters: dict, emit) -> dict | None:
    emit({"type": "status", "text": "场景导演正在把剧情推进到节骨眼…"})
    adv = llm.complete_json(PS.advance_system(cast),
                            PS.advance_user(scene, tp, ledger, state, transcript,
                                            beat_no, MAX_BEATS, cast))
    counters["calls"] += 1
    narration = str(adv.get("narration", ""))
    if adv.get("scene_over"):
        if beat_no == 1:
            counters["warnings"].append("第1回合即收幕（违反推进规矩），本幕无任何行动")
        if narration:
            transcript.append(f"（收幕）{narration}")
        return None

    beat: dict = {"beat": beat_no, "narration": narration,
                  "juncture": str(adv.get("juncture", "")), "warnings": []}
    actor = adv.get("acting_agent", "")
    if actor not in cast.names():
        beat["warnings"].append(f"acting_agent 越界（{actor!r}），落候选人")
        actor = cast.candidate().name
    beat["acting_agent"] = actor

    options = _coerce_options(adv.get("options"))
    if not options:
        raise RuntimeError(f"回合 {beat_no} 没有产出任何可用选项，中止")
    # 控制者增补①：>4 选项越界，大声报错替代 _build_presentations 的隐性 IndexError
    if len(options) > 4:
        raise RuntimeError(f"回合 {beat_no} 产出 {len(options)} 个选项（>4），SM 越界，中止本局")
    if not 3 <= len(options) <= 4:
        beat["warnings"].append(f"选项数异常（{len(options)} 个），照常继续")
    rounds = _build_presentations(options, rng)
    presented = rounds[0]
    beat["options_original"] = options
    beat["options"] = presented
    emit({"type": "beat_open", "scene": scene_idx, "beat": beat_no, "narration": narration,
          "juncture": beat["juncture"], "actor": actor, "options": presented})

    vis_ledger = visible(ledger, actor)
    hid_ledger = [e for e in ledger if e not in vis_ledger]
    emit({"type": "status", "text": f"{actor} 心里正在过这件事…"})
    appr = llm.complete_json(PA.appraisal_system(cast, actor),
                             PA.appraisal_user(scene, transcript, narration,
                                               beat["juncture"], vis_ledger))
    counters["calls"] += 1
    beat["appraisal"] = appr
    emit({"type": "inner", "scene": scene_idx, "beat": beat_no, "actor": actor,
          "emotions": appr.get("emotions", {}),
          "internal_thoughts": appr.get("internal_thoughts", "")})

    emit({"type": "status", "text": f"{actor} 正在换序三问中作答（防位置偏置，取多数票）…"})
    dec, votes, vote_summary = _vote_decision(
        llm=llm, cast=cast, actor=actor,
        internal_thoughts=appr.get("internal_thoughts", ""), scene=scene,
        transcript=transcript, narration=narration, juncture=beat["juncture"],
        vis_ledger=vis_ledger, presentations=rounds, warnings=beat["warnings"])
    counters["calls"] += len(rounds)
    beat["votes"] = votes
    beat["vote_summary"] = vote_summary
    beat["decision"] = dec
    emit({"type": "decision", "scene": scene_idx, "beat": beat_no, "actor": actor,
          "action_id": dec["action_id"], "action": dec.get("action", ""),
          "reasoning": dec.get("reasoning", ""), "confidence": dec.get("confidence"),
          "emotion_tags": dec.get("emotion_tags") or [],
          "vote_verdict": vote_summary["verdict"], "vote_tally": vote_summary["tally"],
          "votes": [{"round": v["round"], "orig_id": v["orig_id"],
                     "position": v["position"], "confidence": v["confidence"]} for v in votes]})

    emit({"type": "status", "text": "理由审计员正在对账…"})
    audit, awarns = AU.run_audit(llm, cast, actor=actor,
                                 internal_thoughts=appr.get("internal_thoughts", ""),
                                 scene=scene, transcript=transcript, narration=narration,
                                 juncture=beat["juncture"], visible_ledger=vis_ledger,
                                 hidden_ledger=hid_ledger, options=presented, decision=dec)
    counters["calls"] += 1
    beat["warnings"].extend(awarns)
    beat["audit"] = audit
    emit({"type": "audit", "scene": scene_idx, "beat": beat_no, **{
        k: audit.get(k) for k in ("verdict", "playbook_match", "playbook_conflict",
                                  "thought_consistency", "thought_note", "fabricated_cues",
                                  "info_overreach", "inner_gap", "note")}})

    transcript.append(
        f"{narration}\n节骨眼：{beat['juncture']}\n"
        f"{actor} 选择：[{dec['action_id']}] {dec.get('action', '')}（理由：{dec.get('reasoning', '')}）")
    _log(f"   回合{beat_no} [{actor}] 三问 {'/'.join(v['orig_id'] for v in votes)}"
         f" → 取原序{vote_summary['winner_orig_id']}（{vote_summary['verdict']}）　审计：{audit['verdict']}")
    return beat


def run_simulation(*, cast: Cast, llm, bank, n_scenes: int = 4, start_tp: str = "C1-01",
                   seed: int | None = None, jd: str = "", emit=None) -> dict:
    """跑一条推演轨迹。emit(event_dict)=直播回调（None 则静默）。"""
    emit = emit or (lambda e: None)
    rng = random.Random(seed)
    state = initial_state()
    ledger: list[dict] = []
    sim_time = ""
    used: set[str] = set()
    tp = bank.by_id(start_tp)
    scenes: list[dict] = []
    counters = {"calls": 0, "warnings": []}
    emit({"type": "run_started", "n_scenes": n_scenes, "start_tp": start_tp, "seed": seed,
          "cast": [{"name": c.name, "kind": c.kind, "role": c.role} for c in cast.members()],
          "candidate": cast.candidate().name})

    for idx in range(n_scenes):
        _log(f"—— 第 {idx + 1}/{n_scenes} 幕 [{tp['category']}] {tp['title']} ——")
        rec: dict = {"index": idx + 1, "turning_point": tp, "warnings": []}

        emit({"type": "status", "text": "场景导演正在搭景…"})
        scene = llm.complete_json(PS.SCENE_INIT_SYSTEM,
                                  PS.scene_init_user(tp, ledger, state, cast,
                                                     jd=jd, prev_time=sim_time))
        counters["calls"] += 1
        rec["scene"] = scene
        if scene.get("sim_time"):
            sim_time = str(scene["sim_time"])
        else:
            rec["warnings"].append("SM 未报 sim_time，本幕沿用上一幕时间标注")
            sim_time = sim_time or f"入职初期（第{idx + 1}幕，SM 未报时间）"
        rec["sim_time"] = sim_time
        _log(f"   场景：[{sim_time}] {scene.get('setting', '?')}")
        emit({"type": "scene_open", "scene": idx + 1, "tp": tp, "sim_time": sim_time,
              "setting": scene.get("setting", ""), "current_scene": scene.get("current_scene", ""),
              "scene_conflict": scene.get("scene_conflict", ""), "npc": scene.get("npc") or []})

        transcript: list[str] = []
        beats: list[dict] = []
        for b in range(1, MAX_BEATS + 1):
            beat = _run_beat(llm=llm, cast=cast, beat_no=b, scene_idx=idx + 1, scene=scene,
                             tp=tp, ledger=ledger, state=state, transcript=transcript,
                             rng=rng, counters=counters, emit=emit)
            if beat is None:
                break
            beats.append(beat)
            rec["warnings"].extend(beat["warnings"])
        rec["beats"] = beats
        if not beats:
            raise RuntimeError(f"第{idx + 1}幕没有任何行动回合，中止")

        emit({"type": "status", "text": "记录者正在收场：判状态灯、估承诺…"})
        settle = llm.complete_json(PS.SETTLE_SYSTEM,
                                   PS.settle_user(scene, transcript, state, cast))
        counters["calls"] += 1
        new_state, evidence, warns = apply_state_deltas(settle.get("state_changes"), state)
        rec["warnings"].extend(warns)
        changed = {k: (state[k], new_state[k]) for k in state if state[k] != new_state[k]}
        if len(changed) >= 3:
            rec["warnings"].append(f"单幕 {len(changed)} 盏灯变化（≥3），判读偏宽嫌疑，需人工复核")
        try:
            commitment = max(0.0, min(5.0, float(settle.get("commitment"))))
        except (TypeError, ValueError):
            rec["warnings"].append(f"commitment 非数（{settle.get('commitment')!r}），记 None")
            commitment = None
        valid_names = set(cast.names()) | {str(n) for n in (scene.get("npc") or [])}
        wit = [str(w) for w in (settle.get("witnesses") or []) if str(w) in valid_names]
        if not wit:
            rec["warnings"].append(f"witnesses 缺失/越界（{settle.get('witnesses')!r}），落全名单")
            wit = cast.names()
        relations = {}
        for name, rel in (settle.get("relations") or {}).items():
            if name in cast.names() and name != cast.candidate().name and isinstance(rel, dict) \
                    and rel.get("attitude") in ("supportive", "neutral", "opposed"):
                relations[name] = {"attitude": rel["attitude"], "evidence": str(rel.get("evidence", ""))}
        rec.update({"states": new_state, "evidence": evidence, "state_changes": changed,
                    "witnesses": wit, "relations": relations, "commitment": commitment,
                    "commitment_rationale": settle.get("commitment_rationale", ""),
                    "scene_summary": settle.get("scene_summary", "")})
        state = new_state
        _log(f"   状态变化：{ {k: f'{a}->{b}' for k, (a, b) in changed.items()} or '无'}；承诺：{commitment}")
        emit({"type": "settle", "scene": idx + 1, "states": new_state,
              "changes": {k: list(v) for k, v in changed.items()},
              "evidence": dict(evidence), "commitment": commitment,
              "rationale": rec["commitment_rationale"], "summary": rec["scene_summary"],
              "witnesses": wit, "sim_time": sim_time,
              "relations": {k: dict(v) for k, v in relations.items()},
              "warnings": rec["warnings"]})

        emit({"type": "status", "text": "记录者正在结算悬而未决的后果…"})
        conseq = llm.complete_json(PS.CONSEQUENCE_SYSTEM,
                                   PS.consequence_user(scene, transcript, rec["scene_summary"]))
        counters["calls"] += 1
        cons = [c for c in (conseq.get("consequences") or [])
                if isinstance(c, dict) and c.get("matter") and c.get("outcome")]
        rec["consequences"] = cons
        ledger.append(entry(sim_time, f"第{idx + 1}幕[{tp['title']}]：{rec['scene_summary']}", wit))
        for c in cons:
            cw = [str(w) for w in (c.get("witnesses") or []) if str(w) in valid_names]
            c["witnesses"] = cw or wit
            ledger.append(entry(sim_time, f"第{idx + 1}幕后果结算：{c['matter']} → {c['outcome']}",
                                c["witnesses"]))
        used.add(tp["id"])
        if cons:
            emit({"type": "consequence", "scene": idx + 1, "consequences": cons})

        if idx + 1 < n_scenes:
            cats = plausible_categories(state, idx + 1)
            cands = bank.candidates(cats, used)
            if not cands:
                rec["warnings"].append("转折点库耗尽，提前收束")
                scenes.append(rec)
                break
            pick = llm.complete_json(PS.NEXT_TP_SYSTEM, PS.next_tp_user(cands, ledger, state))
            counters["calls"] += 1
            cid = pick.get("choice_id")
            if cid not in {c["id"] for c in cands}:
                rec["warnings"].append(f"choice_id 越界（{cid!r}），落候选第一个")
                cid = cands[0]["id"]
            rec["next_tp"] = {"heuristic_categories": cats, "candidates": [c["id"] for c in cands],
                              "choice": cid, "why": pick.get("why", "")}
            emit({"type": "next_tp", "scene": idx + 1, "choice": cid,
                  "why": pick.get("why", ""), "categories": cats})
            tp = bank.by_id(cid)
        scenes.append(rec)
        for w in rec["warnings"]:
            print(f"   [警告] {w}", file=sys.stderr)
        counters["warnings"].extend(rec["warnings"])

    actor_counts: dict[str, int] = {}
    flags = 0
    gaps: dict[str, int] = {}
    vote_stats = {"全票": 0, "多数票": 0, "摇摆": 0}
    pos_counts: dict[str, int] = {}
    for sc in scenes:
        for bt in sc["beats"]:
            actor_counts[bt["acting_agent"]] = actor_counts.get(bt["acting_agent"], 0) + 1
            if bt["audit"].get("verdict") == "黄旗":
                flags += 1
            if (bt["audit"].get("inner_gap") or "无") not in ("无", ""):
                gaps[bt["acting_agent"]] = gaps.get(bt["acting_agent"], 0) + 1
            vote_stats[bt["vote_summary"]["verdict"]] += 1
            for v in bt["votes"]:
                pos_counts[v["position"]] = pos_counts.get(v["position"], 0) + 1
    trace = {"meta": {"model": "deepseek-chat", "n_scenes": len(scenes),
                      "n_llm_calls": counters["calls"], "seed": seed, "max_beats": MAX_BEATS,
                      "cast": [{"name": c.name, "kind": c.kind} for c in cast.members()],
                      "candidate": cast.candidate().name,
                      "vote_rounds": VOTE_ROUNDS, "vote_stats": vote_stats,
                      "vote_position_counts": pos_counts,
                      "actor_counts": actor_counts, "audit_flags": flags, "inner_gaps": gaps,
                      "warnings_total": len(counters["warnings"])},
             "final_state": state, "ledger": ledger, "scenes": scenes}
    emit({"type": "done", "meta": trace["meta"]})
    return trace
