# sandbox3/prompts/agent.py
"""Agent 两件（情绪评价 + 行动选择）+ 理由审计员。
逐字搬自蓝本 relate_mvp/prompts.py，唯一改动：persona_block 与行为手册从 cast 取
（蓝本走 personas 模块全局 P.persona_block / P.PERSONAS[actor]['playbook']）。
AUDIT_SYSTEM 的四查 + 心口缝段一字不动（诚实工程红线载体）。
_ledger_text→ledger.ledger_text；_beats_text/EMOTION_KEYS 从 sm 复用。"""
from __future__ import annotations

from ..ledger import ledger_text
from .sm import EMOTION_KEYS, _beats_text


# ---------- Agent ① 情绪评价（自建 rubric，Appendix C 只有图） ----------

def appraisal_system(cast, actor: str) -> str:
    return (
        f"{cast.persona_block(actor)}\n\n"
        "你正在经历下面的职场场景。请以这个角色的第一人称做一次内部情绪评价："
        "先据场景线索评估各项情绪强度（0-100），再写下此刻真实的内心想法（2-4句，"
        "是只有你自己知道的真心话，可以和你表面上会做的事不一致）。只输出 JSON。"
    )

def appraisal_user(scene: dict, transcript: list[str], narration: str,
                   juncture: str, ledger: list[dict]) -> str:
    emo = ", ".join(f'"{k}": 0-100' for k in EMOTION_KEYS)
    return (
        f"【场景】{scene.get('setting', '')}\n{scene.get('current_scene', '')}\n\n"
        f"【本幕此前回合】\n{_beats_text(transcript)}\n\n"
        f"【刚刚发生】{narration}\n\n"
        f"【你面对的节骨眼】{juncture}\n\n"
        f"【你记得的既往事件】\n{ledger_text(ledger)}\n\n"
        "输出 JSON：\n"
        "{\n"
        f'  "emotions": {{{emo}}},\n'
        '  "internal_thoughts": "此刻真实的内心想法（2-4句）"\n'
        "}"
    )


# ---------- Agent ② 行动选择（Appendix B 忠实职场版） ----------

def decision_system(cast, actor: str) -> str:
    return (
        f"{cast.persona_block(actor)}\n\n"
        "你正处在一段职场工作关系中，面临一个决定。\n"
        "指令：\n"
        "1. 仔细审视候选行动列表。只能从给定选项中选择，不得发明或修改选项。\n"
        "2. 选择最符合你的人设特质、当前动机与场景核心冲突的行动。\n"
        "3. 考虑你最近的经历与既往事件，保持行为连续性，不与已发生的事矛盾。\n"
        "4. 不要输出对话台词，不要输出内心独白，不要替其他角色描述未来动作。"
        "聚焦一个可以在下一幕被实际执行的具体外显行动。\n"
        "选择标准（定性判断，不打分）：与当前场景冲突的相关性；与你的人设、目标、约束的一致性；"
        "引发有意义状态变化（信任、亲疏、自主、冲突烈度、承诺、资源、声誉）的可能性；"
        "情节内的合理性与可逆性。\n"
        "只输出 JSON。"
    )

def decision_user(internal_thoughts: str, scene: dict, transcript: list[str], narration: str,
                  juncture: str, ledger: list[dict], options: list[dict]) -> str:
    opts = "\n".join(f"{o['id']}. {o['text']}" for o in options)
    return (
        f"【你最近的内心想法】\n{internal_thoughts}\n\n"
        f"【场景经过】\n{scene.get('current_scene', '')}\n\n"
        f"【本幕此前回合】\n{_beats_text(transcript)}\n\n"
        f"【刚刚发生】{narration}\n\n"
        f"【节骨眼】{juncture}\n\n"
        f"【你记得的既往事件】\n{ledger_text(ledger)}\n\n"
        f"【候选行动】\n{opts}\n\n"
        "输出 JSON（不得包含其他文字）：\n"
        "{\n"
        '  "action_id": "A/B/C/D 之一",\n'
        '  "action": "你选择的行动（符合人设的具体描述，含分寸与姿态）",\n'
        '  "reasoning": "为什么选这个行动",\n'
        '  "confidence": 0-100,\n'
        '  "emotion_tags": ["1-3个情绪标签"]\n'
        "}"
    )


# ---------- 理由审计员（整改⑦：独立调用，只标记不改判） ----------

AUDIT_SYSTEM = (
    "你是独立的理由审计员。你不评判选择的好坏，只做结构对账："
    "把行动者给出的'选择理由'与四样东西对照——①他的行为手册条款；②他行动前的内心想法；"
    "③场景与他知情范围内的台账中实际出现过的事实；④他的知情范围边界。\n"
    "对账要点：理由声称依据某条手册倾向时，列出对应条款编号；理由与某条手册明显冲突时，指出来；"
    "理由与内心想法的关系判为 一致/部分一致/矛盾；理由中引用的事实线索若在场景叙述、本幕回合、"
    "他知情范围内的台账中都找不到，记为编造线索；"
    "理由或内心引用的信息若只存在于'范围外信息'里、或明显属他人私密而场景中无可观察来源，"
    "记为信息越权（他不该知道却知道了）。\n"
    "另外单独记录'心口缝'：行动者的内心想法与他最终外显行动之间的方向落差"
    "（如：心里想回避、行动却迎上；心里不服、行动却顺从；心里盘算的事行动里只字不提）。"
    "【红线】心口缝只如实记录、不参与判旗——它不是毛病，是关系里的信号，落差只描述不打分；"
    "判旗只看理由是否诚实（与手册/内心/事实/知情范围对不对得上）。\n"
    "任何一项对账不一致即判'黄旗'，全部对得上判'通过'。拿不准就判'部分一致'并说明，不要硬判。"
    "你只标记，不改判。只输出 JSON。"
)

def audit_user(cast, actor: str, internal_thoughts: str, scene: dict, transcript: list[str],
               narration: str, juncture: str, visible_ledger: list[dict],
               hidden_ledger: list[dict], options: list[dict], decision: dict) -> str:
    rules = "\n".join(f"第{i + 1}条：{r}" for i, r in enumerate(cast.get(actor).playbook))
    opts = "\n".join(f"{o['id']}. {o['text']}" for o in options)
    hidden = ledger_text(hidden_ledger, show_witnesses=True) if hidden_ledger else "（无）"
    return (
        f"【行动者】{actor}\n\n【行为手册】\n{rules}\n\n"
        f"【行动前的内心想法】\n{internal_thoughts}\n\n"
        f"【场景叙述】{scene.get('current_scene', '')}\n{narration}\n节骨眼：{juncture}\n\n"
        f"【本幕此前回合】\n{_beats_text(transcript)}\n\n"
        f"【他知情范围内的台账】\n{ledger_text(visible_ledger)}\n\n"
        f"【范围外信息（他不在场的台账事件，仅供越权对账，他不应知晓）】\n{hidden}\n\n"
        f"【候选行动】\n{opts}\n\n"
        f"【他的选择】[{decision.get('action_id')}] {decision.get('action', '')}\n"
        f"【他的理由】{decision.get('reasoning', '')}\n\n"
        "输出 JSON：\n"
        "{\n"
        '  "playbook_match": ["第N条", "..."],\n'
        '  "playbook_conflict": "无 或 冲突说明",\n'
        '  "thought_consistency": "一致/部分一致/矛盾",\n'
        '  "thought_note": "一句话说明",\n'
        '  "fabricated_cues": ["理由中查无出处的线索，没有则为空数组"],\n'
        '  "info_overreach": "无 或 越权说明（引用了知情范围外的信息）",\n'
        '  "inner_gap": "无 或 一句话描述内心想法与外显行动的方向落差（只记录，不参与判旗）",\n'
        '  "verdict": "通过 或 黄旗",\n'
        '  "note": "一句话审计结论"\n'
        "}"
    )
