"""滚动台账=唯一可引用的既往事实。条目带时间戳+在场者；
知情过滤是信息防火墙的数据层：agent 只见亲历条目（物理隔离，不靠模型自觉）。"""
from __future__ import annotations


def entry(time: str, text: str, witnesses: list[str]) -> dict:
    return {"time": time, "text": text, "witnesses": list(witnesses)}


def visible(ledger: list[dict], actor: str) -> list[dict]:
    """角色只记得标注他在场的台账事件。"""
    return [e for e in ledger if actor in (e.get("witnesses") or [])]


def ledger_text(ledger: list[dict], show_witnesses: bool = False) -> str:
    if not ledger:
        return "（尚无可引用的既往事件）"
    lines = []
    for e in ledger:
        w = f"（在场：{'、'.join(e['witnesses'])}）" if show_witnesses and e.get("witnesses") else ""
        lines.append(f"- [{e.get('time', '?')}] {e['text']}{w}")
    return "\n".join(lines)
