# tests/fakes.py
"""FakeLLM：按脚本吐 JSON 的测试替身。只住在 tests/——产品代码不知道它存在。
用法：FakeLLM([dict1, dict2, ...]) 按队列出；或传 router 函数按 prompt 内容路由。"""
from __future__ import annotations
import json


class FakeLLM:
    def __init__(self, script: list[dict] | None = None, router=None):
        self.script = list(script or [])
        self.router = router
        self.calls: list[tuple[str, str]] = []     # (system, user) 留账供断言

    def complete_json(self, system: str, user: str, **kw) -> dict:
        self.calls.append((system, user))
        if self.router is not None:
            out = self.router(system, user)
            if out is not None:
                return out
        if not self.script:
            raise AssertionError(f"FakeLLM 脚本耗尽（第 {len(self.calls)} 次调用）\nsystem={system[:80]}")
        return self.script.pop(0)

    def complete(self, system: str, user: str, **kw) -> str:
        return json.dumps(self.complete_json(system, user, **kw), ensure_ascii=False)
