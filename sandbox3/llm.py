# sandbox3/llm.py
"""DeepSeek 客户端（live-only）。红线：无 mock 回退——失败重试后大声抛错，
绝不静默用假数据冒充推演结果。测试替身在 tests/fakes.py，产品代码无任何 mock 分支。"""
from __future__ import annotations
import json, os, sys, time, urllib.error, urllib.request

from .config import API_URL, MODEL


class LLMError(RuntimeError):
    pass


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        nl = s.find("\n")
        s = s[nl + 1:] if nl != -1 else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


class DeepSeekClient:
    """引擎以依赖收下本对象；换实现=换对象，不开运行时分支。"""

    def __init__(self, api_key: str | None = None):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "") if api_key is None else api_key

    def complete(self, system: str, user: str, *, json_mode: bool = True,
                 temperature: float = 0.7, max_tokens: int = 1200, retries: int = 2) -> str:
        if not self.api_key:
            raise LLMError("DEEPSEEK_API_KEY 未设置——v3 只跑 live，不提供 mock。")
        payload = {"model": MODEL,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}],
                   "temperature": temperature, "max_tokens": max_tokens}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(API_URL, data=body, method="POST",
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {self.api_key}"})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                    OSError, KeyError, IndexError) as e:
                last = e
                print(f"[sandbox3.llm] 第{attempt + 1}次调用失败：{e}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        raise LLMError(f"DeepSeek 调用在 {retries + 1} 次尝试后仍失败：{last}")

    def complete_json(self, system: str, user: str, **kw) -> dict:
        raw = self.complete(system, user, json_mode=True, **kw)
        out = json.loads(_strip_fences(raw))
        if not isinstance(out, dict):
            raise LLMError(f"模型未返回 JSON 对象，得到 {type(out).__name__}")
        return out
