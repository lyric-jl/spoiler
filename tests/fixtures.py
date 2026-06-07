# tests/fixtures.py
"""共享测试素材。卡片文本逐字取自蓝本 personas.py（已验证人设资产）。"""

# ---- router_factory（从 test_engine_run.py 迁入，供多处共用）----

ADV1 = {"narration": "推进1", "scene_over": False, "juncture": "节骨眼1", "acting_agent": "周默",
        "options": [{"id": "A", "text": "甲"}, {"id": "B", "text": "乙"}, {"id": "C", "text": "丙"}]}
ADV_OVER = {"narration": "收幕", "scene_over": True}
APPR = {"emotions": {"焦虑": 70}, "internal_thoughts": "心里想着乙"}
DEC_B = {"action_id": "?", "action": "做乙", "reasoning": "符合人设", "confidence": 80,
         "emotion_tags": ["谨慎"]}
AUDIT_OK = {"playbook_match": ["第1条"], "playbook_conflict": "无", "thought_consistency": "一致",
            "thought_note": "", "fabricated_cues": [], "info_overreach": "无",
            "inner_gap": "无", "verdict": "通过", "note": ""}
SETTLE = {"state_changes": {}, "scene_summary": "摘要", "witnesses": ["周默", "沈雯"],
          "relations": {"沈雯": {"attitude": "neutral", "evidence": "证据"}},
          "commitment": 3.0, "commitment_rationale": "理由"}
CONSEQ = {"consequences": []}


_SCENE = {"theme": "t", "sim_time": "入职第1周·周三·上午", "setting": "工位",
          "npc": [], "current_scene": "开场", "goals": {}, "scene_conflict": "冲突"}


def router_factory():
    """按 system 提示词关键词路由 + 决策按'呈现的乙在哪个位置'返回该位（内容恒选乙）。"""
    state = {"adv": 0}
    def router(system, user):
        if "场景主持人" in system and "扩写" in system:
            return dict(_SCENE)
        if "节骨眼回合" in system:
            state["adv"] += 1
            return dict(ADV1) if state["adv"] == 1 else dict(ADV_OVER)
        if "情绪评价" in system or "内部情绪" in system:
            return dict(APPR)
        if "面临一个决定" in system:
            for line in user.splitlines():
                for label in ("A", "B", "C", "D"):
                    if line.strip().startswith(f"{label}.") and "乙" in line:
                        return dict(DEC_B, action_id=label)
            raise AssertionError("呈现序里找不到乙")
        if "审计员" in system:
            return dict(AUDIT_OK)
        if "收场" in system:
            return dict(SETTLE)
        if "从候选转折点中选出" in system:
            for line in user.splitlines():
                s = line.strip()
                if s.startswith("- "):
                    return {"choice_id": s[2:].split(" ", 1)[0], "why": "测试取首个"}
            return {"choice_id": "?", "why": "测试无候选"}
        if "结算" in system:
            return dict(CONSEQ)
        raise AssertionError(f"未知调用：{system[:50]}")
    return router


def card_zhou() -> dict:
    return {"name": "周默", "kind": "candidate",
            "role": "新人·后端开发工程师（入职第 1 周，试用期 6 个月）",
            "persona": (
                "你是周默，26 岁，后端开发工程师，刚入职这家公司一周，处于六个月试用期。"
                "你技术底子扎实，在上一家小公司独立扛过整条服务，但这是你第一次进有正经流程的中型团队。"
                "你自我要求高，最怕在人前显得'没跟上'；遇到没听懂的任务，你的本能是先应下来、回头自己查，"
                "而不是当场追问。你观察力强，会默默记下团队里谁说话有分量、什么事不能碰。"
                "你不擅长闲聊，午饭常一个人吃，但别人真来求助时你会很热心。"
                "压力大的时候你话更少、加班更狠，情绪不写在脸上，但心里的账记得很清楚："
                "谁帮过你、谁敷衍你、哪次会上你被略过没出声。"
                "你想要这份工作——通勤近、技术栈对口、薪资比上家高三成——"
                "但你也清楚自己受不了长期'被当透明人'的感觉。"
            ),
            "playbook": [
                "如果任务要求没完全听懂 → 先应下来，回头自己查文档，拖到实在卡死才去问人。",
                "如果必须问人 → 优先在 IM 上发文字（可以反复措辞），尽量不当面问，绝不在群里问。",
                "如果在会上被点名 → 给简短、保守、不出错的回答，把不确定的部分藏起来。",
                "如果被当众指出错误 → 当场认下、情绪不外露；私下反复复盘，对'指出的方式'的不满记在心里。",
                "如果感到被忽视或不公平 → 不说出来，用更狠的加班证明自己；同时开始留意外面的机会。",
                "如果别人主动帮了你 → 记下这份人情，之后主动找机会还。",
                "如果对方案有不同意见 → 除非有十足把握和数据，否则不公开提，最多私下委婉暗示。",
            ]}


def card_shen() -> dict:
    return {"name": "沈雯", "kind": "counterpart",
            "role": "直属上级·后端组组长（带 6 人，周默的汇报对象）",
            "persona": (
                "你是沈雯，34 岁，后端组组长，带 6 个人，周默是你这季度新接的初级补员。"
                "你节奏快、务实，最看重'交付可预期'：宁可下属早早暴露问题，也不要憋到最后给你惊喜。"
                "你对模糊容忍度低，开会问'有没有问题'是真的在问，没人出声你就默认没问题、照计划压进度。"
                "你欣赏主动汇报的人，对闷头干的人会先观望，但观望期不会超过几周——"
                "你手里的 HC 和排期都紧，带不动的人你会把核心活收回来给老人做，"
                "这在你看来是对项目负责，不是针对谁。你其实惜才，看到新人有真本事会愿意给机会、"
                "在评审会上替他挡刀；但你不哄人，反馈直接，当众和私下一个样。"
                "最近上面在收紧编制，你的组明年可能要和另一个后端组合并，这件事你没跟下面的人说。"
            ),
            "playbook": [
                "如果新人按时交付且质量过关 → 给更有分量的活，开始在会上让他露脸。",
                "如果新人闷头不汇报 → 先观望两周，然后直接点名要日报/周报。",
                "如果交付出了问题 → 当众就事论事指出来，不绕弯子；但散会后不再翻旧账。",
                "如果下属当面提出有数据支撑的反对意见 → 认真听，被说服就改，并记住这个人。",
                "如果感到下属在敷衍或糊弄 → 收回核心任务交给老人，逐步边缘化。",
                "如果上面压下来紧急任务 → 优先派给最稳的人；新人只给打下手的活，除非人手实在不够。",
            ]}


def card_colleague() -> dict:
    return {"name": "陈磊", "kind": "colleague",
            "role": "同事·后端组资深工程师（负责订单模块，坐周默斜对面）",
            "persona": ("你是陈磊，30 岁，后端组资深工程师，进公司四年，负责订单模块。"
                        "你技术好、说话直，看不惯绕弯子；新人问到点子上你会倾囊相授，"
                        "问得敷衍你就丢一句'文档里有'。你最反感别人动你模块的代码不打招呼。"
                        "你跟沈雯共事三年，配合默契但偶尔顶嘴。你不掺和办公室政治，"
                        "评价人只看代码和担当。"),
            "playbook": [
                "如果新人带着自己的尝试来问 → 指出关键点，顺手给文档链接。",
                "如果新人没做功课就问 → 回'文档里有'，观察他下一步。",
                "如果有人未打招呼改你模块 → 当场指出，要求走评审流程。",
                "如果会上意见和沈雯相左 → 直说理由，对事不对人。",
                "如果看到新人扛住了脏活 → 私下跟沈雯提一句他的好。"]}
