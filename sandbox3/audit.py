# sandbox3/audit.py
"""理由审计员（独立调用，只标记不改判）。verdict 越界保守落黄旗。"""
from __future__ import annotations

from .prompts import agent as A

VERDICTS = ("通过", "黄旗")


def run_audit(llm, cast, *, actor: str, internal_thoughts: str, scene: dict,
              transcript: list[str], narration: str, juncture: str,
              visible_ledger: list[dict], hidden_ledger: list[dict],
              options: list[dict], decision: dict) -> tuple[dict, list[str]]:
    audit = llm.complete_json(
        A.AUDIT_SYSTEM,
        A.audit_user(cast, actor, internal_thoughts, scene, transcript, narration,
                     juncture, visible_ledger, hidden_ledger, options, decision))
    warns = []
    if audit.get("verdict") not in VERDICTS:
        warns.append(f"审计 verdict 越界（{audit.get('verdict')!r}），保守记黄旗")
        audit["verdict"] = "黄旗"
    return audit, warns
