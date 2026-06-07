# relate_mvp/states.py
"""八状态灯（职场版）+ 枚举 + 下一幕类别启发式。
对应 RELATE-Sim Appendix D 的职场化映射（见精读笔记 §9）：
clarity→role_clarity（角色清晰度，对上文献 role clarity）、
constraints→embeddedness（投入绑定）、network→团队接纳（对上 social acceptance）、
breakup_marker→exit_marker（离职信号）。"""
from __future__ import annotations

STATE_ENUMS: dict[str, list[str]] = {
    "conflict":       ["none", "brewing", "active", "unresolved", "repaired", "unknown"],
    "repair_outcome": ["none", "attempted", "successful", "failed", "unknown"],
    "role_clarity":   ["unclear", "tacit", "explicit", "unknown"],
    "embeddedness":   ["none", "emerging", "accrued", "unknown"],
    "alternatives":   ["quiet", "salient", "hot", "unknown"],
    "transition":     ["none", "upcoming", "underway", "unknown"],
    "network":        ["supportive", "neutral", "opposed", "mixed", "unknown"],
    "exit_marker":    ["none", "soft", "hard", "unknown"],
}

STATE_LABELS = {
    "conflict": "冲突", "repair_outcome": "修复结果", "role_clarity": "角色清晰度",
    "embeddedness": "投入绑定", "alternatives": "外部机会", "transition": "变动",
    "network": "团队接纳", "exit_marker": "离职信号",
}

STATE_DESCRIPTIONS = {
    "conflict": "批评、防御、轻蔑、冷处理等使分歧升级的张力（none无/brewing酝酿/active爆发/unresolved未解决/repaired已修复）",
    "repair_outcome": "道歉、补救、立新规矩等修复动作的结果（none无/attempted尝试过/successful成功/failed失败）",
    "role_clarity": "新人的职责、期望、评价标准是否被明确（unclear不清/tacit心照不宣/explicit已明示）",
    "embeddedness": "把新人和团队绑在一起的实际投入——独立负责的模块、专属知识、关键排期（none无/emerging萌芽/accrued已累积）",
    "alternatives": "新人对外部机会的留意程度或团队物色替代者的信号（quiet安静/salient显现/hot炽热）",
    "transition": "重塑关系语境的变动——组织调整、换上级、项目切换（none无/upcoming将至/underway进行中）",
    "network": "团队其他人对新人的接纳氛围（supportive支持/neutral中立/opposed排斥/mixed混杂）",
    "exit_marker": "这段雇佣关系走向终止的信号——萌生去意、明确表达、被边缘化（none无/soft软信号/hard硬信号）",
}


def initial_state() -> dict:
    """入职第一天的合理初值：无冲突、角色不清、无绑定、无去意。"""
    return {"conflict": "none", "repair_outcome": "none", "role_clarity": "unclear",
            "embeddedness": "none", "alternatives": "quiet", "transition": "none",
            "network": "neutral", "exit_marker": "none"}


def apply_state_deltas(raw, prev: dict) -> tuple[dict, dict, list[str]]:
    """差量制（毛病单v2-②）：只接收"本幕有证据需要变化的灯"，其余自动沿用上一幕；
    未知灯/越界值/退回 unknown 一律拒收并告警。返回 (state, evidence, warnings)。"""
    out, evidence, warns = dict(prev), {}, []
    for key, item in (raw or {}).items():
        if key not in STATE_ENUMS:
            warns.append(f"状态差量含未知灯 {key!r}，忽略")
            continue
        v = item.get("new") if isinstance(item, dict) else item
        ev = item.get("evidence", "") if isinstance(item, dict) else ""
        if v not in STATE_ENUMS[key]:
            warns.append(f"状态 {key} 差量越界（{v!r}），沿用上一幕 {prev[key]!r}")
            continue
        if v == "unknown" and prev[key] != "unknown":
            warns.append(f"状态 {key} 试图退回 unknown（上一幕为 {prev[key]!r}），拒收")
            continue
        if v == prev[key]:
            continue
        out[key] = v
        evidence[key] = str(ev)
    return out, evidence, warns


def plausible_categories(state: dict, scene_idx: int) -> list[str]:
    """轻量启发式：当前状态灯 → 下一幕候选转折点类别（对应论文 §4.2 的 lightweight heuristic）。"""
    cats: list[str] = []
    if state["conflict"] in ("active", "unresolved") or state["repair_outcome"] == "failed":
        cats.append("冲突与修复")
    if state["exit_marker"] in ("soft", "hard") or state["alternatives"] in ("salient", "hot"):
        cats.extend(["压力测试", "现代职场"])
    if state["role_clarity"] == "unclear":
        cats.append("磨合建制")
    if not cats:
        cats = ["初来乍到", "磨合建制"] if scene_idx <= 1 else ["压力测试", "深化里程碑"]
    return cats
